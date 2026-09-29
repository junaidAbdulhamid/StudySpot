import pandas as pd
from conftest import config, location, raw_snapshot
from ml.src.cleaning import normalize
from ml.src.config import utc
from ml.src.targets import build_targets

T = utc("2026-09-15T14:00:00Z")


def _target_at(raw, times=(T,), **cfg_overrides):
    tables, _ = normalize(raw)
    return build_targets(tables, pd.DatetimeIndex(times), config(**cfg_overrides)).iloc[0]


def test_trusted_observation_wins_as_tier_a():
    raw = raw_snapshot(
        [location()],
        observations=[
            dict(
                id="o1",
                location_id="loc-a",
                observed_at=utc("2026-09-15T13:58:00Z"),
                created_at=utc("2026-09-15T13:58:00Z"),
                occupancy_percent=45,
                occupied_seats=45,
                total_seats=100,
                source="manual",
            )
        ],
        # An estimate is also present but must be overridden by the trusted observation.
        estimates=[
            dict(
                id="e1",
                location_id="loc-a",
                estimated_at=utc("2026-09-15T13:59:00Z"),
                created_at=utc("2026-09-15T13:59:00Z"),
                occupancy_percent=90,
                confidence_score=0.95,
                signal_count=10,
                source="crowd_report",
            )
        ],
    )
    row = _target_at(raw)
    assert row.target_quality == "A_TRUSTED"
    assert row.target_source == "trusted_observation"
    assert row.target_occupancy == 45
    assert row.target_weight == 1.0


def test_strong_consensus_estimate_is_tier_b():
    reports = [
        dict(
            id=f"r{i}",
            location_id="loc-a",
            submitted_at=utc("2026-09-15T13:59:00Z"),
            created_at=utc("2026-09-15T13:59:00Z"),
            normalized_value=50,
            location_verified=True,
            user_reliability_at_submission=0.9,
        )
        for i in range(4)
    ]
    raw = raw_snapshot(
        [location()],
        estimates=[
            dict(
                id="e1",
                location_id="loc-a",
                estimated_at=utc("2026-09-15T13:59:00Z"),
                created_at=utc("2026-09-15T13:59:00Z"),
                occupancy_percent=50,
                confidence_score=0.95,
                signal_count=4,
                source="crowd_report",
            )
        ],
        reports=reports,
    )
    row = _target_at(raw)
    assert row.target_quality == "B_STRONG_CONSENSUS"
    assert row.target_source == "crowd_consensus"
    assert row.target_weight == 0.75


def test_weak_estimate_without_consensus_is_tier_c():
    raw = raw_snapshot(
        [location()],
        estimates=[
            dict(
                id="e1",
                location_id="loc-a",
                estimated_at=utc("2026-09-15T13:59:00Z"),
                created_at=utc("2026-09-15T13:59:00Z"),
                occupancy_percent=50,
                confidence_score=0.4,
                signal_count=1,
                source="crowd_report",
            )
        ],
    )
    row = _target_at(raw)
    assert row.target_quality == "C_WEAK_ESTIMATE"
    assert row.target_source == "weak_estimate"
    assert row.target_weight == 0.35


def test_no_evidence_is_tier_d_and_null():
    raw = raw_snapshot([location()])
    row = _target_at(raw)
    assert row.target_quality == "D_UNKNOWN"
    assert row.target_source == "unknown"
    assert pd.isna(row.target_occupancy)
    assert row.target_weight == 0.0


def test_seed_estimates_never_become_targets():
    raw = raw_snapshot(
        [location()],
        estimates=[
            dict(
                id="e1",
                location_id="loc-a",
                estimated_at=utc("2026-09-15T13:59:00Z"),
                created_at=utc("2026-09-15T13:59:00Z"),
                occupancy_percent=77,
                confidence_score=0.99,
                signal_count=20,
                source="seed",
            )
        ],
    )
    row = _target_at(raw)
    assert row.target_quality == "D_UNKNOWN"
