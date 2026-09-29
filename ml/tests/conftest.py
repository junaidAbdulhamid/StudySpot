"""Fixture builders for a fully controlled raw snapshot, independent of any database."""

import pandas as pd
import pytest
from ml.src.config import PipelineConfig, utc
from ml.src.snapshot import ALLOWED

SOURCE_TABLES = ("estimates", "observations", "reports", "checkins", "validations")


def location(
    location_id="loc-a",
    campus_id="campus-1",
    building_id="building-1",
    capacity=100,
    noise_level="quiet",
    floor="1",
    timezone="America/New_York",
    opening_time="07:00:00",
    closing_time="23:00:00",
    is_active=True,
    available_at="2020-01-01T00:00:00Z",
):
    return {
        "location_id": location_id,
        "campus_id": campus_id,
        "building_id": building_id,
        "capacity": capacity,
        "noise_level": noise_level,
        "floor": floor,
        "timezone": timezone,
        "opening_time": opening_time,
        "closing_time": closing_time,
        "is_active": is_active,
        "available_at": utc(available_at),
    }


def raw_snapshot(locations, **tables):
    """Build a complete, schema-correct raw snapshot dict for every ALLOWED table.

    ``tables`` supplies row lists for any of estimates/observations/reports/checkins/
    validations/calendar/weather; anything omitted becomes an empty, correctly-shaped frame.
    """
    frames = {"locations": pd.DataFrame(locations)}
    for name in ALLOWED:
        if name == "locations":
            continue
        rows = tables.get(name, [])
        columns = (
            sorted(ALLOWED[name])
            if name not in SOURCE_TABLES
            else list(__import__("ml.src.extraction", fromlist=["SOURCES"]).SOURCES[name][2])
        )
        frames[name] = pd.DataFrame(rows, columns=columns)
    return frames


def config(start="2026-09-15T00:00:00Z", end="2026-09-16T00:00:00Z", **overrides):
    return PipelineConfig(start=start, end=end, **overrides)


@pytest.fixture
def one_location():
    return [location()]


@pytest.fixture
def two_locations():
    return [location(location_id="loc-a"), location(location_id="loc-b", building_id="building-2")]
