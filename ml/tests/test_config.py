import pytest
from ml.src.config import PipelineConfig


def base(**overrides):
    values = {"start": "2026-09-01T00:00:00Z", "end": "2026-09-02T00:00:00Z"}
    values.update(overrides)
    return PipelineConfig(**values)


def test_valid_config_constructs():
    cfg = base()
    assert cfg.bucket_minutes == 15
    assert cfg.lookback_minutes == max(cfg.lag_minutes) + cfg.estimate_max_age_minutes


def test_naive_timestamp_rejected():
    with pytest.raises(ValueError):
        base(start="2026-09-01T00:00:00")


def test_start_must_precede_end():
    with pytest.raises(ValueError):
        base(start="2026-09-02T00:00:00Z", end="2026-09-01T00:00:00Z")


def test_bucket_minutes_must_divide_a_day():
    with pytest.raises(ValueError):
        base(bucket_minutes=7)


@pytest.mark.parametrize("field", ["horizons", "lag_minutes", "rolling_minutes", "report_windows"])
def test_windows_must_be_unique_positive_multiples(field):
    with pytest.raises(ValueError):
        base(**{field: (15, 15)})
    with pytest.raises(ValueError):
        base(**{field: (17,)})
    with pytest.raises(ValueError):
        base(**{field: (-15,)})


def test_minimum_quality_cannot_be_unknown_tier():
    with pytest.raises(ValueError):
        base(minimum_quality="D_UNKNOWN")


def test_target_weights_must_be_four_values_in_range():
    with pytest.raises(ValueError):
        base(target_weights=(1.0, 0.5, 0.0))
    with pytest.raises(ValueError):
        base(target_weights=(1.5, 0.75, 0.35, 0.0))


def test_split_fractions_must_leave_room_for_three_splits():
    with pytest.raises(ValueError):
        base(train_fraction=0.9, validation_fraction=0.2)


def test_split_boundaries_require_both_or_neither():
    with pytest.raises(ValueError):
        base(train_end="2026-09-01T12:00:00Z")


def test_split_boundaries_must_be_ordered_inside_range():
    with pytest.raises(ValueError):
        base(train_end="2026-09-01T18:00:00Z", validation_end="2026-09-01T12:00:00Z")
    cfg = base(train_end="2026-09-01T12:00:00Z", validation_end="2026-09-01T18:00:00Z")
    assert cfg.train_end == "2026-09-01T12:00:00Z"
