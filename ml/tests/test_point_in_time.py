"""Mandatory point-in-time correctness tests (spec: "Feature aggregation at 2:00 PM must
include a 1:55 PM report. It must NOT include a 2:05 PM report.") Repeated for every event
type, plus the event-time-vs-knowledge-time distinction: a report that *happened* before T
but that StudySpot only *learned about* after T must not leak into T's features either.
"""

import pandas as pd
from conftest import config, location, raw_snapshot
from ml.src.cleaning import normalize
from ml.src.config import utc
from ml.src.features import build_features

T = utc("2026-09-15T14:00:00Z")


def _features_at(raw, times=(T,)):
    tables, _ = normalize(raw)
    loc = tables["locations"].iloc[0].to_dict()
    return build_features(loc, tables, pd.DatetimeIndex(times), config())


def test_report_before_cutoff_is_included_report_after_is_excluded():
    raw = raw_snapshot(
        [location()],
        reports=[
            dict(
                id="before",
                location_id="loc-a",
                submitted_at=utc("2026-09-15T13:55:00Z"),
                created_at=utc("2026-09-15T13:55:00Z"),
                normalized_value=40,
                location_verified=True,
                user_reliability_at_submission=0.9,
            ),
            dict(
                id="after",
                location_id="loc-a",
                submitted_at=utc("2026-09-15T14:05:00Z"),
                created_at=utc("2026-09-15T14:05:00Z"),
                normalized_value=90,
                location_verified=True,
                user_reliability_at_submission=0.9,
            ),
        ],
    )
    row = _features_at(raw).iloc[0]
    assert row.report_count_30m == 1
    assert row.mean_report_value_30m == 40


def test_estimate_after_cutoff_is_excluded():
    raw = raw_snapshot(
        [location()],
        estimates=[
            dict(
                id="before",
                location_id="loc-a",
                estimated_at=utc("2026-09-15T13:59:00Z"),
                created_at=utc("2026-09-15T13:59:00Z"),
                occupancy_percent=30,
                confidence_score=0.8,
                signal_count=4,
                source="crowd_report",
            ),
            dict(
                id="after",
                location_id="loc-a",
                estimated_at=utc("2026-09-15T14:01:00Z"),
                created_at=utc("2026-09-15T14:01:00Z"),
                occupancy_percent=99,
                confidence_score=0.8,
                signal_count=4,
                source="crowd_report",
            ),
        ],
    )
    row = _features_at(raw).iloc[0]
    assert row.occupancy_now == 30


def test_checkin_and_checkout_after_cutoff_are_excluded():
    raw = raw_snapshot(
        [location()],
        checkins=[
            dict(
                id="before",
                location_id="loc-a",
                checked_in_at=utc("2026-09-15T13:50:00Z"),
                created_at=utc("2026-09-15T13:50:00Z"),
                checked_out_at=None,
                expires_at=utc("2026-09-15T17:50:00Z"),
                updated_at=utc("2026-09-15T13:50:00Z"),
            ),
            dict(
                id="after",
                location_id="loc-a",
                checked_in_at=utc("2026-09-15T14:05:00Z"),
                created_at=utc("2026-09-15T14:05:00Z"),
                checked_out_at=None,
                expires_at=utc("2026-09-15T18:05:00Z"),
                updated_at=utc("2026-09-15T14:05:00Z"),
            ),
        ],
    )
    row = _features_at(raw).iloc[0]
    assert row.checkins_started_15m == 1  # 13:50 is inside (13:45, 14:00]
    assert row.active_checkins == 1  # but it is still active and counted
    assert row.checkins_started_30m == 1


def test_validation_after_cutoff_is_excluded():
    raw = raw_snapshot(
        [location()],
        validations=[
            dict(
                id="before",
                location_id="loc-a",
                submitted_at=utc("2026-09-15T13:58:00Z"),
                created_at=utc("2026-09-15T13:58:00Z"),
                validation_type="accurate",
            ),
            dict(
                id="after",
                location_id="loc-a",
                submitted_at=utc("2026-09-15T14:02:00Z"),
                created_at=utc("2026-09-15T14:02:00Z"),
                validation_type="more_crowded",
            ),
        ],
    )
    row = _features_at(raw).iloc[0]
    assert row.validations_accurate_30m == 1
    assert row.validations_more_crowded_30m == 0


def test_event_time_before_cutoff_but_learned_late_is_excluded():
    """A report that *happened* at 13:55 but was only submitted to the server (created_at)
    at 14:10 was not knowable at 14:00 and must not appear in the 14:00 row."""
    raw = raw_snapshot(
        [location()],
        reports=[
            dict(
                id="late-known",
                location_id="loc-a",
                submitted_at=utc("2026-09-15T13:55:00Z"),
                created_at=utc("2026-09-15T14:10:00Z"),
                normalized_value=95,
                location_verified=True,
                user_reliability_at_submission=0.9,
            )
        ],
    )
    row = _features_at(raw).iloc[0]
    assert row.report_count_30m == 0
    assert pd.isna(row.mean_report_value_30m)


def test_location_metadata_known_only_after_its_available_at():
    raw = raw_snapshot([location(available_at="2026-09-15T14:30:00Z")])
    row = _features_at(raw).iloc[0]
    assert bool(row.metadata_missing) is True
    assert pd.isna(row.capacity)
