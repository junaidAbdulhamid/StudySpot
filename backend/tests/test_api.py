from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings, get_settings
from app.models import (
    Favorite,
    OccupancyEstimate,
    OccupancyPrediction,
    StudyLocation,
    UserPreference,
)
from app.models.enums import ConfidenceLevel, OccupancySource
from app.seed.run import seed
from app.utils.occupancy import classify_occupancy

API = "/api/v1"
USER = f"{API}/me"


def test_health_docs(client):
    assert client.get(f"{API}/health").json() == {
        "status": "ok",
        "database": "connected",
        "postgis": "enabled",
    }
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    spec = client.get("/openapi.json").json()
    assert f"{API}/locations/{{location_id}}/predictions" in spec["paths"]


def test_catalog(client):
    campuses = client.get(f"{API}/campuses").json()
    assert campuses["total"] == 1
    assert (
        client.get(f"{API}/campuses/gmu-fairfax").json()["data"]["timezone"] == "America/New_York"
    )
    assert client.get(f"{API}/campuses/missing").status_code == 404
    assert client.get(f"{API}/buildings?campus_id=gmu-fairfax").json()["total"] == 5
    assert client.get(f"{API}/buildings/fenwick-library").status_code == 200
    assert client.get(f"{API}/buildings/missing").status_code == 404


def test_list_detail(client):
    response = client.get(f"{API}/locations")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 12
    assert len(body["items"]) == 12
    detail = client.get(f"{API}/locations/zone-1").json()["data"]
    assert detail["current_occupancy"] is None
    assert detail["campus"]["id"] == "gmu-fairfax"
    assert detail["building"]["name"] == "Fenwick Library"
    assert len(detail["predictions"]) == 4
    assert "walking_minutes" not in detail
    assert len(detail["historical"]) == 8
    assert detail["hours"] == {"open": "07:00", "close": "00:00"}
    missing = client.get(f"{API}/locations/missing")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "LOCATION_NOT_FOUND"


@pytest.mark.parametrize(
    ("query", "total"),
    [
        ("search=FENWICK", 4),
        ("search=floor%204", 1),
        ("noise_level=quiet", 6),
        ("amenities=whiteboards,group-rooms", 3),
        ("max_occupancy=39", 0),
        ("min_occupancy=65&max_occupancy=84", 0),
        ("building_id=fenwick-library", 4),
        ("campus_id=missing", 0),
        ("amenities=nonexistent", 0),
        ("search=%25", 0),
        ("search=%27%20OR%201%3D1--", 0),
    ],
)
def test_filters(client, query, total):
    response = client.get(f"{API}/locations?{query}")
    assert response.status_code == 200, response.text
    assert response.json()["total"] == total


def test_open_now(client):
    opened = client.get(f"{API}/locations?open_now=true").json()["total"]
    closed = client.get(f"{API}/locations?open_now=false").json()["total"]
    assert opened + closed == 12


def test_pagination(client):
    first = client.get(f"{API}/locations?page_size=5&page=1").json()
    second = client.get(f"{API}/locations?page_size=5&page=2").json()
    assert first["total"] == second["total"] == 12
    assert len(first["items"]) == len(second["items"]) == 5
    assert not {x["id"] for x in first["items"]} & {x["id"] for x in second["items"]}
    assert client.get(f"{API}/locations?page=100").json()["items"] == []


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page_size=101",
        "noise_level=loud",
        "min_occupancy=-1",
        "max_occupancy=101",
        "min_occupancy=60&max_occupancy=20",
    ],
)
def test_invalid_query(client, query):
    response = client.get(f"{API}/locations?{query}")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_me(client):
    data = client.get(USER).json()["data"]
    assert data["id"] == "dev-studyspot"
    assert data["email"] == "dev@studyspot.local"
    assert data["display_name"] == "Alex Morgan"


def test_update_me(client):
    updated = client.patch(USER, json={"display_name": "New Name"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["display_name"] == "New Name"
    assert client.get(USER).json()["data"]["display_name"] == "New Name"
    assert client.patch(USER, json={"display_name": ""}).status_code == 422
    assert client.patch(USER, json={"display_name": None}).status_code == 422
    assert client.patch(USER, json={"avatar_url": "not-https"}).status_code == 422
    assert client.patch(USER, json={"unknown": 1}).status_code == 422
    for protected in (
        "id",
        "auth_provider_id",
        "email",
        "points",
        "reliability_score",
        "onboarding_completed",
    ):
        assert client.patch(USER, json={protected: "forbidden"}).status_code == 422


def test_favorites(client):
    before = client.get(f"{USER}/favorites").json()["total"]
    one = client.post(f"{USER}/favorites/zone-3")
    two = client.post(f"{USER}/favorites/zone-3")
    assert one.status_code == two.status_code == 200
    assert one.json()["data"]["id"] == two.json()["data"]["id"]
    assert client.get(f"{USER}/favorites").json()["total"] == before + 1
    assert client.delete(f"{USER}/favorites/zone-3").status_code == 204
    assert client.delete(f"{USER}/favorites/zone-3").status_code == 204
    assert client.post(f"{USER}/favorites/missing").status_code == 404


def test_preferences(client):
    original = client.get(f"{USER}/preferences").json()["data"]
    update = client.patch(
        f"{USER}/preferences",
        json={
            "noise_preference": "moderate",
            "study_style": "group",
            "max_walking_minutes": 15,
            "preferred_amenities": ["outlets", "whiteboards"],
        },
    )
    assert update.status_code == 200, update.text
    data = client.get(f"{USER}/preferences").json()["data"]
    assert data["noise_preference"] == "moderate"
    assert data["study_style"] == "group"
    assert {a["slug"] for a in data["preferred_amenities"]} == {"outlets", "whiteboards"}
    assert data["study_duration_hours"] == original["study_duration_hours"]
    assert client.get(USER).json()["data"]["onboarding_completed"] is True
    assert (
        client.patch(f"{USER}/preferences", json={"preferred_amenities": []}).json()["data"][
            "preferred_amenities"
        ]
        == []
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"max_walking_minutes": 0},
        {"noise_preference": None},
        {"noise_preference": "loud"},
        {"preferred_amenities": ["missing"]},
        {"unknown": 1},
    ],
)
def test_invalid_preferences(client, patch):
    assert client.patch(f"{USER}/preferences", json=patch).status_code == 422


def test_predictions(client, db):
    response = client.get(f"{API}/locations/zone-1/predictions?hours_ahead=4")
    assert response.status_code == 200
    predictions = response.json()["data"]
    assert len(predictions) == 4
    assert all(p["source"] == "seed" and p["model_version"] == "seed-v1" for p in predictions)
    assert len(client.get(f"{API}/locations/zone-1/predictions?hours_ahead=1").json()["data"]) == 1
    assert client.get(f"{API}/locations/missing/predictions").status_code == 404
    assert client.get(f"{API}/locations/zone-1/predictions?hours_ahead=0").status_code == 422
    for item in db.scalars(
        select(OccupancyPrediction).where(OccupancyPrediction.location_id == "zone-1")
    ):
        item.target_time -= timedelta(days=1)
    db.commit()
    assert client.get(f"{API}/locations/zone-1/predictions").json()["data"] == []


def test_latest_occupancy_and_null(client, db):
    db.add(
        OccupancyEstimate(
            location_id="zone-1",
            occupancy_percent=90,
            confidence=ConfidenceLevel.HIGH,
            source=OccupancySource.MANUAL,
            estimated_at=datetime.now(UTC),
        )
    )
    db.commit()
    assert (
        client.get(f"{API}/locations/zone-1").json()["data"]["current_occupancy"]["percent"] == 90
    )
    assert "zone-1" not in {
        x["id"] for x in client.get(f"{API}/locations?max_occupancy=39").json()["items"]
    }
    db.execute(text("DELETE FROM occupancy_estimates WHERE location_id='zone-1'"))
    db.commit()
    assert client.get(f"{API}/locations/zone-1").json()["data"]["current_occupancy"] is None


def test_postgis_and_indexes(db):
    row = db.execute(
        text(
            "SELECT ST_SRID(geo_point::geometry), ST_X(geo_point::geometry), ST_Y(geo_point::geometry), longitude, latitude FROM study_locations WHERE id='zone-1'"
        )
    ).one()
    assert row[0] == 4326 and row[1] == row[3] and row[2] == row[4]
    assert "gist" in db.scalar(
        text("SELECT indexdef FROM pg_indexes WHERE indexname='ix_study_locations_geo_point'")
    )
    db.execute(text("UPDATE study_locations SET longitude=-77.3 WHERE id='zone-1'"))
    assert (
        db.scalar(text("SELECT ST_X(geo_point::geometry) FROM study_locations WHERE id='zone-1'"))
        == -77.3
    )


@pytest.mark.parametrize("percent", [-1, 101])
def test_occupancy_constraint(db, percent):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            OccupancyEstimate(
                location_id="zone-1",
                occupancy_percent=percent,
                confidence=ConfidenceLevel.HIGH,
                source=OccupancySource.MANUAL,
                estimated_at=datetime.now(UTC),
            )
        )
        db.flush()


def test_unique_favorite_and_foreign_key(db):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Favorite(user_id="dev-studyspot", location_id="zone-1"))
        db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Favorite(user_id="missing", location_id="zone-1"))
        db.flush()


def test_idempotent_seed_preserves_user_choices(db):
    preference = db.scalar(select(UserPreference).where(UserPreference.user_id == "dev-studyspot"))
    preference.max_walking_minutes = 15
    db.execute(text("DELETE FROM favorites WHERE user_id='dev-studyspot' AND location_id='zone-1'"))
    db.commit()
    seed(db, "dev-studyspot")
    seed(db, "dev-studyspot")
    assert db.scalar(select(func.count()).select_from(StudyLocation)) == 12
    assert db.scalar(select(func.count()).select_from(OccupancyPrediction)) == 48
    assert db.scalar(select(func.count()).select_from(OccupancyEstimate)) == 0
    assert preference.max_walking_minutes == 15
    assert (
        db.scalar(
            select(Favorite).where(
                Favorite.user_id == "dev-studyspot", Favorite.location_id == "zone-1"
            )
        )
        is None
    )


def test_list_has_bounded_query_count(client, db):
    queries = []
    connection = db.connection()

    def count(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    event.listen(connection, "before_cursor_execute", count)
    try:
        assert client.get(f"{API}/locations?page_size=100").status_code == 200
        assert len(queries) <= 6
    finally:
        event.remove(connection, "before_cursor_execute", count)


@pytest.mark.parametrize(
    ("percent", "expected"),
    [
        (0, "available"),
        (39, "available"),
        (40, "moderate"),
        (64, "moderate"),
        (65, "busy"),
        (84, "busy"),
        (85, "full"),
        (100, "full"),
    ],
)
def test_classification(percent, expected):
    assert classify_occupancy(percent) == expected


def test_me_requires_bearer_token(anonymous_client):
    assert anonymous_client.get(USER).status_code == 401
    assert anonymous_client.get(f"{USER}/favorites").status_code == 401
    response = anonymous_client.get(USER)
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_rejects_malformed_authorization(anonymous_client):
    assert anonymous_client.get(USER, headers={"Authorization": "Basic abc"}).status_code == 401
    huge_token = "a" * 20000
    assert (
        anonymous_client.get(USER, headers={"Authorization": f"Bearer {huge_token}"}).status_code
        == 401
    )


def test_me_returns_503_when_supabase_unconfigured(anonymous_client, monkeypatch):
    # A real Supabase project may be configured in .env for local development;
    # force the unconfigured case explicitly so this test doesn't depend on it.
    from app.core import auth as auth_module

    unconfigured = Settings(
        supabase_url="", supabase_anon_key="", database_url=get_settings().database_url
    )
    monkeypatch.setattr(auth_module, "get_settings", lambda: unconfigured)
    response = anonymous_client.get(USER, headers={"Authorization": "Bearer irrelevant-token"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_UNAVAILABLE"


def test_production_rejects_demo_identity():
    with pytest.raises(ValueError):
        Settings(app_env="production", debug=False, dev_user_enabled=True)


def test_production_rejects_insecure_auth_url():
    with pytest.raises(ValueError):
        Settings(
            app_env="production",
            debug=False,
            dev_user_enabled=False,
            supabase_url="http://127.0.0.1:8002/test-auth",
        )


def test_errors_do_not_expose_exception_details(client, db, monkeypatch):
    from sqlalchemy.exc import OperationalError

    monkeypatch.setattr(
        db,
        "execute",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OperationalError("secret SQL", {}, Exception("secret credentials"))
        ),
    )
    response = client.get(f"{API}/health")
    assert response.status_code == 503
    assert "secret" not in response.text


def test_migration_roundtrip(engine):
    import os
    import subprocess
    import sys
    from uuid import uuid4

    from sqlalchemy import create_engine

    from tests.conftest import url

    name = f"studyspot_migration_{uuid4().hex[:10]}_test"
    admin = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", hide_parameters=True
    )
    with admin.connect() as connection:
        quoted = connection.dialect.identifier_preparer.quote(name)
        connection.execute(text(f"CREATE DATABASE {quoted}"))
    target = url.set(database=name)
    env = {**os.environ, "DATABASE_URL": target.render_as_string(hide_password=False)}
    try:
        for args in [("upgrade", "head"), ("downgrade", "base"), ("upgrade", "head"), ("check",)]:
            result = subprocess.run(
                [sys.executable, "-m", "alembic", *args], env=env, capture_output=True, text=True
            )
            assert result.returncode == 0, result.stderr
        engine = create_engine(target, hide_parameters=True)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT PostGIS_Version()"))
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version")) == "25630308138f"
            )
        engine.dispose()
    finally:
        with admin.connect() as connection:
            connection.execute(text(f"DROP DATABASE {quoted}"))
        admin.dispose()
