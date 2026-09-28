import logging

import pytest
from sqlalchemy import select, text

from app.core.logging import RedactQueryString
from app.models import StudyLocation, User, UserPreference

PATH = "/api/v1/locations/nearby"


def params(client):
    location = client.get("/api/v1/locations/zone-1").json()["data"]
    return {"latitude": location["latitude"], "longitude": location["longitude"]}


def test_nearby_order_radius_filters(client):
    origin = params(client)
    response = client.get(PATH, params=origin)
    assert response.status_code == 200, response.text
    rows = response.json()["data"]
    assert len(rows) == 12
    assert rows[0]["distance_meters"] == pytest.approx(0, abs=0.01)
    assert [(r["distance_meters"], r["id"]) for r in rows] == sorted(
        (r["distance_meters"], r["id"]) for r in rows
    )
    assert rows[-1]["distance_meters"] > rows[0]["distance_meters"]
    assert all(r["amenities"] and r["current_occupancy"] for r in rows)
    limited = client.get(PATH, params={**origin, "radius_meters": 1}).json()["data"]
    assert 0 < len(limited) < len(rows)
    for filters in [
        {"amenities": "outlets,whiteboards"},
        {"noise_level": "quiet"},
        {"max_occupancy": 40},
        {"search": "whiteboard"},
        {"open_now": True},
    ]:
        nearby = client.get(PATH, params={**origin, **filters}).json()["data"]
        listed = client.get("/api/v1/locations", params=filters).json()["items"]
        assert {r["id"] for r in nearby} == {r["id"] for r in listed}
    assert len(client.get(PATH, params={**origin, "limit": 2}).json()["data"]) == 2
    assert client.get(PATH, params={"latitude": 0, "longitude": 0}).json()["data"] == []


@pytest.mark.parametrize(
    "key,value",
    [
        ("latitude", 91),
        ("latitude", -91),
        ("longitude", 181),
        ("longitude", -181),
        ("latitude", "nan"),
        ("radius_meters", 10001),
        ("radius_meters", 0),
        ("limit", 101),
        ("limit", 0),
    ],
)
def test_nearby_validation(client, key, value):
    assert client.get(PATH, params={**params(client), key: value}).status_code == 422


def test_known_points_boundary(client, db):
    # Approximately 111.31949 meters along the equator on WGS84.
    a, b = db.get(StudyLocation, "zone-1"), db.get(StudyLocation, "zone-2")
    a.latitude, a.longitude = 0, 0
    b.latitude, b.longitude = 0, 0.001
    db.flush()
    origin = {"latitude": 0, "longitude": 0, "radius_meters": 112}
    rows = client.get(PATH, params=origin).json()["data"]
    assert [r["id"] for r in rows] == [a.id, b.id]
    assert rows[1]["distance_meters"] == pytest.approx(111.31949, abs=0.01)
    assert len(client.get(PATH, params={**origin, "radius_meters": 111.31}).json()["data"]) == 1
    assert len(client.get(PATH, params={**origin, "radius_meters": 111.33}).json()["data"]) == 2
    index = (
        db.execute(
            text(
                "SELECT indexdef FROM pg_indexes WHERE tablename='study_locations' AND indexdef ILIKE '%gist%'"
            )
        )
        .scalars()
        .all()
    )
    assert any("geo_point" in value for value in index)


def test_coordinates_not_persisted_or_logged(client, db):
    before = list(db.scalars(select(User)))
    client.get(PATH, params=params(client))
    assert len(list(db.scalars(select(User)))) == len(before)
    for model in (User, UserPreference):
        assert not {"latitude", "longitude", "geo_point"}.intersection(
            model.__table__.columns.keys()
        )
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        '%s - "%s %s HTTP/%s" %s',
        ("client", "GET", PATH + "?latitude=38.831&longitude=-77.307", "1.1", 200),
        None,
    )
    RedactQueryString().filter(record)
    assert "latitude" not in record.getMessage()
    assert "38.831" not in record.getMessage()
    assert PATH in record.getMessage()
