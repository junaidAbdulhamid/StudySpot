import pandas as pd
import pytest
from conftest import config, location, raw_snapshot
from ml.src.cleaning import normalize
from ml.src.config import utc
from ml.src.features import build_features

BASE = utc("2026-09-15T13:00:00Z")
BUCKETS = [BASE + pd.Timedelta(minutes=15 * i) for i in range(5)]  # 13:00 .. 14:00
VALUES = [10, 20, 30, 40, 50]


def _frame():
    estimates = [
        dict(
            id=f"e{i}",
            location_id="loc-a",
            estimated_at=t,
            created_at=t,
            occupancy_percent=v,
            confidence_score=0.9,
            signal_count=5,
            source="crowd_report",
        )
        for i, (t, v) in enumerate(zip(BUCKETS, VALUES, strict=True))
    ]
    raw = raw_snapshot([location()], estimates=estimates)
    tables, _ = normalize(raw)
    loc = tables["locations"].iloc[0].to_dict()
    return build_features(loc, tables, pd.DatetimeIndex(BUCKETS), config())


def test_occupancy_now_matches_the_estimate_at_each_bucket():
    frame = _frame()
    assert list(frame.occupancy_now) == VALUES


def test_lag_60m_looks_back_exactly_four_buckets():
    frame = _frame()
    last = frame.iloc[-1]
    assert last.occupancy_lag_60m == VALUES[0]
    assert last.occupancy_trend_60m == VALUES[-1] - VALUES[0]


def test_lag_is_missing_before_enough_history_exists():
    frame = _frame()
    assert frame.iloc[0].occupancy_lag_60m_missing
    assert pd.isna(frame.iloc[0].occupancy_lag_60m)


def test_rolling_mean_30m_covers_the_last_two_buckets():
    frame = _frame()
    last = frame.iloc[-1]
    assert last.occupancy_rolling_mean_30m == pytest.approx((VALUES[-1] + VALUES[-2]) / 2)
    assert last.occupancy_rolling_count_30m == 2
