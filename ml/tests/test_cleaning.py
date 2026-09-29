import pandas as pd
import pytest
from conftest import location, raw_snapshot
from ml.src.cleaning import normalize
from ml.src.config import utc


def test_valid_rows_pass_through_untouched():
    raw = raw_snapshot(
        [location()],
        estimates=[
            dict(
                id="e1",
                location_id="loc-a",
                estimated_at=utc("2026-09-15T14:00:00Z"),
                created_at=utc("2026-09-15T14:00:00Z"),
                occupancy_percent=40,
                confidence_score=0.8,
                signal_count=3,
                source="crowd_report",
            )
        ],
    )
    tables, quality = normalize(raw)
    assert len(tables["estimates"]) == 1
    assert quality["estimates"] == {"input": 1, "duplicates_removed": 0, "invalid_removed": 0}


def test_out_of_range_occupancy_is_quarantined():
    raw = raw_snapshot(
        [location()],
        estimates=[
            dict(
                id="e1",
                location_id="loc-a",
                estimated_at=utc("2026-09-15T14:00:00Z"),
                created_at=utc("2026-09-15T14:00:00Z"),
                occupancy_percent=180,
                confidence_score=0.8,
                signal_count=3,
                source="crowd_report",
            ),
            dict(
                id="e2",
                location_id="loc-a",
                estimated_at=utc("2026-09-15T14:05:00Z"),
                created_at=utc("2026-09-15T14:05:00Z"),
                occupancy_percent=40,
                confidence_score=0.8,
                signal_count=3,
                source="crowd_report",
            ),
        ],
    )
    tables, quality = normalize(raw)
    assert len(tables["estimates"]) == 1
    assert tables["estimates"].iloc[0].id == "e2"
    assert quality["estimates"]["invalid_removed"] == 1


def test_impossible_observation_seat_counts_are_quarantined():
    raw = raw_snapshot(
        [location()],
        observations=[
            dict(
                id="o1",
                location_id="loc-a",
                observed_at=utc("2026-09-15T14:00:00Z"),
                created_at=utc("2026-09-15T14:00:00Z"),
                occupancy_percent=90,
                occupied_seats=120,
                total_seats=100,
                source="manual",
            )
        ],
    )
    tables, _ = normalize(raw)
    assert tables["observations"].empty


def test_checkin_chronology_violation_is_quarantined():
    raw = raw_snapshot(
        [location()],
        checkins=[
            dict(
                id="c1",
                location_id="loc-a",
                checked_in_at=utc("2026-09-15T14:00:00Z"),
                created_at=utc("2026-09-15T14:00:00Z"),
                checked_out_at=utc("2026-09-15T13:00:00Z"),
                expires_at=utc("2026-09-15T18:00:00Z"),
                updated_at=utc("2026-09-15T13:00:00Z"),
            )
        ],
    )
    tables, _ = normalize(raw)
    assert tables["checkins"].empty


def test_duplicate_locations_raise():
    raw = raw_snapshot([location(), location()])
    with pytest.raises(ValueError, match="Duplicate locations"):
        normalize(raw)


def test_conflicting_event_ids_raise():
    raw = raw_snapshot(
        [location()],
        reports=[
            dict(
                id="r1",
                location_id="loc-a",
                submitted_at=utc("2026-09-15T14:00:00Z"),
                created_at=utc("2026-09-15T14:00:00Z"),
                normalized_value=40,
                location_verified=True,
                user_reliability_at_submission=0.9,
            ),
            dict(
                id="r1",
                location_id="loc-a",
                submitted_at=utc("2026-09-15T14:05:00Z"),
                created_at=utc("2026-09-15T14:05:00Z"),
                normalized_value=60,
                location_verified=True,
                user_reliability_at_submission=0.9,
            ),
        ],
    )
    with pytest.raises(ValueError, match="Conflicting event IDs"):
        normalize(raw)


def test_naive_timestamp_is_rejected():
    raw = raw_snapshot([location()])
    raw["reports"] = pd.DataFrame(
        [
            dict(
                id="r1",
                location_id="loc-a",
                submitted_at=pd.Timestamp("2026-09-15T14:00:00"),
                created_at=pd.Timestamp("2026-09-15T14:00:00"),
                normalized_value=40,
                location_verified=True,
                user_reliability_at_submission=0.9,
            )
        ]
    )
    with pytest.raises(ValueError, match="Naive timestamp"):
        normalize(raw)


def test_report_referencing_unknown_location_is_quarantined():
    raw = raw_snapshot(
        [location()],
        reports=[
            dict(
                id="r1",
                location_id="loc-does-not-exist",
                submitted_at=utc("2026-09-15T14:00:00Z"),
                created_at=utc("2026-09-15T14:00:00Z"),
                normalized_value=40,
                location_verified=True,
                user_reliability_at_submission=0.9,
            )
        ],
    )
    tables, _ = normalize(raw)
    assert tables["reports"].empty
