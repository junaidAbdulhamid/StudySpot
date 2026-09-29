"""Operating-hour math, overnight closing times, and DST transitions (America/New_York)."""

import math

import pytest
from ml.src.config import utc
from ml.src.features import operating_hours

TZ = "America/New_York"


def test_same_day_hours_open_and_closed():
    is_open, since, until = operating_hours(utc("2026-09-15T16:00:00Z"), "07:00:00", "23:00:00", TZ)
    assert is_open and since == pytest.approx(300) and until == pytest.approx(660)
    is_open, since, until = operating_hours(utc("2026-09-15T05:00:00Z"), "07:00:00", "23:00:00", TZ)
    assert not is_open


def test_overnight_closing_time_crosses_midnight():
    # 7:00 AM - 1:00 AM local; at 12:30 AM local the location is still open from "yesterday".
    is_open, since, _ = operating_hours(utc("2026-09-16T04:30:00Z"), "07:00:00", "01:00:00", TZ)
    assert is_open
    assert since == pytest.approx(17.5 * 60)
    # Just after closing (1:30 AM local), before the next 7:00 AM opening.
    is_open, _, _ = operating_hours(utc("2026-09-16T05:30:00Z"), "07:00:00", "01:00:00", TZ)
    assert not is_open


def test_spring_forward_nonexistent_closing_time_shifts_forward():
    # 2026-03-08: US Eastern clocks jump from 2:00 AM to 3:00 AM; 2:30 AM never occurs.
    # A closing time inside the gap must resolve (shift forward), not crash.
    is_open, since, until = operating_hours(utc("2026-03-08T06:00:00Z"), "01:00:00", "02:30:00", TZ)
    assert is_open
    assert since == pytest.approx(0, abs=0.01)
    assert until == pytest.approx(60, abs=0.01)  # pandas shifts 2:30 to first valid time, 3:00 EDT


def test_fall_back_ambiguous_opening_time_resolves_to_earliest_occurrence():
    # 2026-11-01: 1:00-2:00 AM Eastern occurs twice; the opening should resolve to the
    # earliest (daylight) occurrence so the daily window doesn't shrink unexpectedly.
    is_open, since, until = operating_hours(utc("2026-11-01T12:00:00Z"), "01:30:00", "23:00:00", TZ)
    assert is_open
    assert since == pytest.approx(390, abs=0.01)
    assert until == pytest.approx(960, abs=0.01)


def test_closed_location_reports_nan_offsets():
    is_open, since, until = operating_hours(utc("2026-09-15T05:00:00Z"), "07:00:00", "23:00:00", TZ)
    assert not is_open
    assert math.isnan(since) and math.isnan(until)
