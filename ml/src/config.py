"""All modeling choices are explicit and serialized into each build manifest."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

PIPELINE_VERSION = "0.6.0"
SCHEMA_VERSION = "1"


def utc(value):
    value = pd.Timestamp(value)
    if value.tzinfo is None:
        raise ValueError("Timestamp must include a UTC offset")
    return value.tz_convert("UTC")


@dataclass(frozen=True)
class PipelineConfig:
    start: str
    end: str
    bucket_minutes: int = 15
    horizons: tuple[int, ...] = (15, 30, 60, 120)
    lag_minutes: tuple[int, ...] = (15, 30, 60, 120)
    rolling_minutes: tuple[int, ...] = (30, 60, 120)
    report_windows: tuple[int, ...] = (15, 30, 60)
    estimate_max_age_minutes: int = 30
    observation_max_age_minutes: int = 15
    confidence_half_life_minutes: int = 45
    consensus_min_reports: int = 3
    consensus_min_confidence: float = 0.7
    consensus_max_std: float = 15
    consensus_min_verified_fraction: float = 0.6
    minimum_quality: str = "C_WEAK_ESTIMATE"
    target_weights: tuple[float, ...] = (1.0, 0.75, 0.35, 0.0)
    min_location_targets: int = 20
    exclude_closed: bool = True
    required_features: tuple[str, ...] = ()
    train_fraction: float = 0.7
    validation_fraction: float = 0.15
    train_end: str | None = None
    validation_end: str | None = None
    holdout_locations: tuple[str, ...] = ()
    location_ids: tuple[str, ...] = ()
    max_grid_rows: int = 2_000_000

    def __post_init__(self):
        if utc(self.start) >= utc(self.end):
            raise ValueError("start must precede end")
        if self.bucket_minutes <= 0 or 1440 % self.bucket_minutes:
            raise ValueError("bucket_minutes must divide a day")
        for seq in (self.horizons, self.lag_minutes, self.rolling_minutes, self.report_windows):
            if (
                not seq
                or len(set(seq)) != len(seq)
                or any(x <= 0 or x % self.bucket_minutes for x in seq)
            ):
                raise ValueError("Windows must be unique positive multiples of bucket_minutes")
        if self.minimum_quality not in QUALITIES[:-1]:
            raise ValueError("minimum_quality must be A, B, or C")
        if len(self.target_weights) != 4 or any(not 0 <= x <= 1 for x in self.target_weights):
            raise ValueError("Four target weights in [0,1] required")
        if (
            not 0 < self.train_fraction < 1
            or not 0 < self.validation_fraction < 1 - self.train_fraction
        ):
            raise ValueError("Invalid split fractions")
        if bool(self.train_end) != bool(self.validation_end):
            raise ValueError("Supply both date split boundaries")
        if self.train_end and not utc(self.start) < utc(self.train_end) < utc(
            self.validation_end
        ) < utc(self.end):
            raise ValueError("Split boundaries must be ordered inside build range")
        if (
            min(
                self.estimate_max_age_minutes,
                self.observation_max_age_minutes,
                self.confidence_half_life_minutes,
                self.consensus_min_reports,
                self.min_location_targets,
                self.max_grid_rows,
            )
            <= 0
        ):
            raise ValueError("Limits must be positive")
        if (
            not 0 <= self.consensus_min_confidence <= 1
            or not 0 <= self.consensus_min_verified_fraction <= 1
            or self.consensus_max_std < 0
        ):
            raise ValueError("Invalid consensus thresholds")

    @property
    def lookback_minutes(self):
        return (
            max(*self.lag_minutes, *self.rolling_minutes, *self.report_windows)
            + self.estimate_max_age_minutes
        )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_file(cls, path: Path, **overrides):
        values = json.loads(path.read_text()) if path else {}
        values.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**values)


QUALITIES = ("A_TRUSTED", "B_STRONG_CONSENSUS", "C_WEAK_ESTIMATE", "D_UNKNOWN")
