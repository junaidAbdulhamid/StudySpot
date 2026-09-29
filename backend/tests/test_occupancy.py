from datetime import UTC, datetime, timedelta

from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select

from app.models import CheckIn, CrowdReport, OccupancyEstimate, StudyLocation, User
from app.models.enums import CheckInStatus, CrowdLevel
from app.services import occupancy as occupancy_module
from app.services.occupancy import OccupancyService, cache_key, report_limit_key
from app.services.occupancy_estimator import ReportSignal, effective_confidence, estimate_occupancy

API = "/api/v1"


def test_estimator_unknown_recency_agreement_and_manual():
    now = datetime.now(UTC)
    assert estimate_occupancy(now, []).percent is None
    fresh = ReportSignal(50, now, 0.5, True)
    one = estimate_occupancy(now, [fresh])
    many = estimate_occupancy(now, [fresh] * 8)
    conflict = estimate_occupancy(now, [fresh] * 4 + [ReportSignal(92, now, 0.5, True)] * 4)
    old = estimate_occupancy(now, [ReportSignal(50, now - timedelta(minutes=90), 0.5, True)])
    assert one.percent == 50
    assert many.confidence_score > one.confidence_score > old.confidence_score
    assert conflict.confidence_score < many.confidence_score
    assert (
        estimate_occupancy(
            now, [ReportSignal(20, now, 0.5, True), ReportSignal(92, now, 0.5, True)]
        ).percent
        == 56
    )
    assert estimate_occupancy(now, [fresh] * 8 + [ReportSignal(92, now, 0.5, True)]).percent == 50
    assert estimate_occupancy(now, [], manual_percent=0, manual_at=now).percent == 0
    assert estimate_occupancy(now, [], manual_percent=100, manual_at=now).percent == 100
    assert estimate_occupancy(now, [fresh], active_checkins=20).percent == 50
    assert effective_confidence(0.8, now - timedelta(minutes=60), now)[0] < 0.4


def test_checkin_report_validation_and_privacy(client, db):
    initial = client.get(f"{API}/locations/zone-1/occupancy")
    assert initial.status_code == 200
    assert initial.json()["data"]["occupancy_percent"] is None
    assert initial.json()["data"]["signal_summary"]["recent_reports"] == 0
    response = client.post(
        f"{API}/checkins",
        json={
            "location_id": "zone-1",
            "latitude": 38.8315,
            "longitude": -77.3075,
        },
    )
    assert response.status_code == 200, response.text
    checkin = response.json()["data"]
    assert checkin["status"] == "active"
    assert client.get(f"{API}/me/checkins/active").json()["data"]["id"] == checkin["id"]
    assert db.scalar(select(CheckIn).where(CheckIn.id == checkin["id"])).user_id == "dev-studyspot"
    assert (
        client.get(f"{API}/locations/zone-1/occupancy").json()["data"]["occupancy_percent"] is None
    )
    report = client.post(
        f"{API}/crowd-reports", json={"location_id": "zone-1", "crowd_level": "moderate"}
    )
    assert report.status_code == 200, report.text
    assert db.scalar(select(CrowdReport).where(CrowdReport.id == report.json()["data"]["id"]))
    assert (
        client.post(
            f"{API}/crowd-reports", json={"location_id": "zone-1", "crowd_level": "busy"}
        ).status_code
        == 429
    )
    current = client.get(f"{API}/locations/zone-1/occupancy").json()["data"]
    assert current["occupancy_percent"] == 50
    assert current["signal_summary"]["recent_reports"] == 1
    assert current["signal_summary"]["active_checkins"] == 1
    assert "user_id" not in current
    validation = client.post(
        f"{API}/occupancy-validations",
        json={
            "location_id": "zone-1",
            "estimate_id": current["estimate_id"],
            "validation_type": "accurate",
        },
    )
    assert validation.status_code == 200, validation.text
    assert client.post(
        f"{API}/occupancy-validations",
        json={
            "location_id": "zone-1",
            "estimate_id": current["estimate_id"],
            "validation_type": "accurate",
        },
    ).status_code in (409, 429)
    next_estimate = client.get(f"{API}/locations/zone-1/occupancy").json()["data"]["estimate_id"]
    assert (
        client.post(
            f"{API}/occupancy-validations",
            json={
                "location_id": "zone-1",
                "estimate_id": next_estimate,
                "validation_type": "accurate",
            },
        ).status_code
        == 429
    )
    assert client.post(f"{API}/checkins/{checkin['id']}/checkout").status_code == 200
    assert client.get(f"{API}/me/checkins/active").json()["data"] is None
    assert client.post(f"{API}/checkins/{checkin['id']}/checkout").status_code == 200


def test_checkin_switch_and_ownership(client, db):
    first = client.post(f"{API}/checkins", json={"location_id": "zone-1"}).json()["data"]
    second = client.post(f"{API}/checkins", json={"location_id": "zone-2"}).json()["data"]
    assert db.get(CheckIn, first["id"]).status == CheckInStatus.COMPLETED
    assert second["id"] != first["id"]
    other = User(id="occupancy-other", email="other@example.edu", display_name="Other")
    db.add(other)
    db.flush()
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_current_user
    from app.core.database import get_db
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: other
    with TestClient(app) as another:
        assert another.post(f"{API}/checkins/{second['id']}/checkout").status_code == 404


def test_expired_checkin_is_not_active(client, db):
    row = client.post(f"{API}/checkins", json={"location_id": "zone-1"}).json()["data"]
    db.get(CheckIn, row["id"]).checked_in_at = datetime.now(UTC) - timedelta(hours=5)
    db.get(CheckIn, row["id"]).expires_at = datetime.now(UTC) - timedelta(hours=1)
    db.commit()
    assert client.get(f"{API}/me/checkins/active").json()["data"] is None
    assert OccupancyService(db).expire_due() == 1
    assert db.get(CheckIn, row["id"]).status == CheckInStatus.EXPIRED


def test_unauthorized_invalid_location_and_proximity(client, anonymous_client, db):
    for path, body in (
        ("checkins", {"location_id": "zone-1"}),
        ("crowd-reports", {"location_id": "zone-1", "crowd_level": "busy"}),
        (
            "occupancy-validations",
            {"location_id": "zone-1", "estimate_id": "x", "validation_type": "accurate"},
        ),
    ):
        assert anonymous_client.post(f"{API}/{path}", json=body).status_code == 401
    assert client.post(f"{API}/checkins", json={"location_id": "missing"}).status_code == 404
    assert (
        client.post(
            f"{API}/crowd-reports", json={"location_id": "zone-1", "crowd_level": "invalid"}
        ).status_code
        == 422
    )
    assert (
        client.post(f"{API}/checkins", json={"location_id": "zone-1", "latitude": 0}).status_code
        == 422
    )
    location = db.get(StudyLocation, "zone-1")
    near = client.post(
        f"{API}/checkins",
        json={
            "location_id": "zone-1",
            "latitude": location.latitude,
            "longitude": location.longitude,
        },
    ).json()["data"]
    assert near["location_verified"]
    far = client.post(
        f"{API}/checkins", json={"location_id": "zone-2", "latitude": 0, "longitude": 0}
    ).json()["data"]
    assert not far["location_verified"]
    assert not hasattr(db.get(CheckIn, far["id"]), "latitude")


def test_redis_cache_hit_miss_and_failure(client, db, monkeypatch):
    client.post(f"{API}/crowd-reports", json={"location_id": "zone-1", "crowd_level": "busy"})

    class FakeRedis:
        def __init__(self):
            self.values = {}
            self.ttl = None
            self.fail = False

        def get(self, key):
            if self.fail:
                raise RedisConnectionError("unavailable")
            return self.values.get(key)

        def setex(self, key, ttl, value):
            self.values[key] = value
            self.ttl = ttl

    fake = FakeRedis()
    settings = occupancy_module.get_settings()
    monkeypatch.setattr(
        occupancy_module,
        "get_settings",
        lambda: settings.model_copy(update={"app_env": "development"}),
    )
    monkeypatch.setattr(occupancy_module, "redis_client", lambda: fake)
    service = OccupancyService(db)
    first = service.current_payload("zone-1")
    assert first["occupancy_percent"] == 75
    assert fake.ttl == 60 and cache_key("zone-1") in fake.values
    assert report_limit_key("u", "z") == "studyspot:ratelimit:report:u:z"
    monkeypatch.setattr(
        service, "current", lambda _: (_ for _ in ()).throw(AssertionError("DB hit"))
    )
    assert service.current_payload("zone-1") == first
    fake.fail = True
    monkeypatch.setattr(
        service, "current", lambda _: db.get(OccupancyEstimate, first["estimate_id"])
    )
    assert service.current_payload("zone-1") == first


def test_reliability_changes_only_after_three_distinct_reports(db):
    users = [
        User(id=f"consensus-{i}", email=f"consensus-{i}@example.edu", display_name="Test")
        for i in range(3)
    ]
    db.add_all(users)
    db.flush()
    service = OccupancyService(db)
    service.report(users[0], "zone-1", CrowdLevel.MODERATE)
    service.report(users[1], "zone-1", CrowdLevel.MODERATE)
    assert users[0].reliability_score == 0.5
    service.report(users[2], "zone-1", CrowdLevel.MODERATE)
    assert users[0].reliability_score == 0.51
    assert users[1].reliability_score == 0.51
    assert users[2].reliability_score == 0.51
