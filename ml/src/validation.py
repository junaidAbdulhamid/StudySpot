"""Fatal schema/privacy/leakage checks, plus descriptive quality and coverage."""

import numpy as np
import pandas as pd

from ml.src.config import QUALITIES, utc
from ml.src.registry import feature_registry


def validate_frame(frame, config):
    registry = feature_registry(config)
    metadata = {
        "location_id",
        "timestamp",
        "feature_max_available_at",
        "target_occupancy",
        "target_quality",
        "target_weight",
        "target_source",
        "sample_weight",
        "split",
        "sparse_location",
        "is_training_eligible",
        "location_holdout",
    }
    for horizon in config.horizons:
        metadata.update(
            {
                f"target_{horizon}m",
                f"target_{horizon}m_quality",
                f"target_{horizon}m_weight",
                f"target_{horizon}m_source",
                f"target_{horizon}m_timestamp",
                f"eligible_{horizon}m",
            }
        )
    if set(frame.columns) != set(registry) | metadata:
        raise ValueError(
            f"Schema/privacy mismatch: {set(frame.columns) ^ (set(registry) | metadata)}"
        )
    if frame.empty:
        raise ValueError("Empty dataset")
    if frame.duplicated(["location_id", "timestamp"]).any():
        raise ValueError("Duplicate location/timestamp rows")
    if frame.location_id.isna().any() or frame.timestamp.isna().any():
        raise ValueError("Null row key")
    if str(frame.timestamp.dtype) != "datetime64[ns, UTC]":
        raise ValueError("Timestamp must have UTC nanosecond dtype")
    if not frame.timestamp.eq(frame.timestamp.dt.floor(f"{config.bucket_minutes}min")).all():
        raise ValueError("Off-grid timestamp")
    if not ((frame.timestamp >= utc(config.start)) & (frame.timestamp < utc(config.end))).all():
        raise ValueError("Row outside build range")
    if (frame.feature_max_available_at > frame.timestamp).any():
        raise ValueError("Feature knowledge-time leakage")
    for column, spec in registry.items():
        values = frame[column].dropna()
        if spec["type"] in ("float", "int"):
            if not pd.api.types.is_numeric_dtype(frame[column]) or not np.isfinite(values).all():
                raise ValueError(f"Invalid numeric type/value: {column}")
            if spec["type"] == "int" and not (values % 1 == 0).all():
                raise ValueError(f"Noninteger {column}")
        elif spec["type"] == "bool" and not values.isin([True, False]).all():
            raise ValueError(f"Invalid boolean {column}")
        elif spec["type"] == "string" and not values.map(lambda x: isinstance(x, str)).all():
            raise ValueError(f"Invalid categorical {column}")
        if spec["range"] and not values.between(*spec["range"]).all():
            raise ValueError(f"Out of range: {column}")
    for column in ["capacity", "active_checkins", "recent_signal_count", "signal_age_seconds"] + [
        x
        for x in registry
        if x.startswith(("report_count_", "checkins_started_", "checkouts_", "validations_"))
    ]:
        if (frame[column].dropna() < 0).any():
            raise ValueError(f"Negative {column}")
    for value, quality, weight in [("target_occupancy", "target_quality", "target_weight")] + [
        (f"target_{h}m", f"target_{h}m_quality", f"target_{h}m_weight") for h in config.horizons
    ]:
        if (
            not frame[value].dropna().between(0, 100).all()
            or not frame[quality].isin(QUALITIES).all()
        ):
            raise ValueError("Invalid target value/quality")
        expected = frame[quality].map(dict(zip(QUALITIES, config.target_weights, strict=True)))
        if (
            not frame[weight].eq(expected).all()
            or not frame[value].isna().eq(frame[quality].eq(QUALITIES[3])).all()
        ):
            raise ValueError("Target quality/weight/nullability mismatch")
    if not frame.split.isin(["train", "validation", "test"]).all():
        raise ValueError("Invalid split")
    previous = None
    for split in ("train", "validation", "test"):
        part = frame[frame.split == split]
        if len(part):
            if previous is not None and previous >= part.timestamp.min():
                raise ValueError("Split chronology violation")
            previous = part.timestamp.max()
    for horizon in config.horizons:
        if (
            not frame[f"target_{horizon}m_timestamp"]
            .eq(frame.timestamp + pd.Timedelta(minutes=horizon))
            .all()
        ):
            raise ValueError("Forecast alignment violation")
        for split in ("train", "validation"):
            later = frame[
                frame.split.isin(["validation", "test"] if split == "train" else ["test"])
            ]
            eligible = frame[(frame.split == split) & frame[f"eligible_{horizon}m"]]
            if (
                len(later)
                and (eligible[f"target_{horizon}m_timestamp"] >= later.timestamp.min()).any()
            ):
                raise ValueError("Forecast labels cross split boundary")
    return {
        "schema": "passed",
        "privacy": "passed",
        "point_in_time": "passed",
        "splits": "passed",
        "duplicates": 0,
    }


def quality_report(frame, cleaning, tables, config):
    def counts(column):
        return {str(k): int(v) for k, v in frame[column].value_counts(dropna=False).items()}

    warnings = []
    if frame.sparse_location.any():
        warnings.append("Sparse locations excluded from training")
    if not frame.target_quality.eq("A_TRUSTED").any():
        warnings.append("No trusted exact observations")
    missingness = frame.isna().mean().to_dict()
    if any(x > 0.5 for x in missingness.values()):
        warnings.append("Some columns have more than 50% missing values")
    for split in ("train", "validation", "test"):
        if not ((frame.split == split) & frame.is_training_eligible).any():
            warnings.append(f"No eligible {split} rows; collect more history")
    return {
        "rows": len(frame),
        "locations": frame.location_id.nunique(),
        "training_eligible": int(frame.is_training_eligible.sum()),
        "start": str(frame.timestamp.min()),
        "end": str(frame.timestamp.max()),
        "cleaning": cleaning,
        "warnings": warnings,
        "missingness": missingness,
        "coverage": {
            key: counts(key)
            for key in (
                "location_id",
                "day_of_week",
                "hour_of_day",
                "target_quality",
                "academic_period",
                "month",
                "split",
            )
        },
        "rows_by_utc_date": frame.timestamp.dt.date.astype(str).value_counts().to_dict(),
        "target_distribution": pd.cut(
            frame.target_occupancy,
            [-0.001, 20, 40, 60, 80, 100],
            labels=["0-20", "20-40", "40-60", "60-80", "80-100"],
        )
        .value_counts()
        .to_dict(),
        "horizons": {
            str(h): {
                "coverage": float(frame[f"target_{h}m"].notna().mean()),
                "eligible": int(frame[f"eligible_{h}m"].sum()),
                "quality": counts(f"target_{h}m_quality"),
            }
            for h in config.horizons
        },
        "contribution_coverage": {
            name: table.groupby("location_id").size().to_dict()
            for name, table in tables.items()
            if "location_id" in table and name != "locations"
        },
        "verified_report_fraction": tables["reports"]
        .groupby("location_id")
        .location_verified.mean()
        .to_dict(),
        "high_confidence_estimate_fraction": float(
            (frame.current_confidence_score >= config.consensus_min_confidence).mean()
        ),
    }
