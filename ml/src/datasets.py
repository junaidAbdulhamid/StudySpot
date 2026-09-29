"""Reproducible builds, immutable version directories, and the Phase 7 loading contract."""

import json
import logging
import os
import shutil
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from ml.src.cleaning import normalize
from ml.src.config import PIPELINE_VERSION, QUALITIES, SCHEMA_VERSION, PipelineConfig, utc
from ml.src.features import build_features
from ml.src.registry import feature_registry
from ml.src.snapshot import checksum, read_snapshot, safe_version, write_snapshot
from ml.src.targets import build_targets
from ml.src.validation import quality_report, validate_frame

logger = logging.getLogger(__name__)


def build_frame(raw, config):
    tables, cleaning = normalize(raw)
    start, end = utc(config.start), utc(config.end)
    times = pd.date_range(
        (start - pd.Timedelta(minutes=config.lookback_minutes)).floor(
            f"{config.bucket_minutes}min"
        ),
        end + pd.Timedelta(minutes=max(config.horizons)),
        freq=f"{config.bucket_minutes}min",
        inclusive="left",
    )
    locations = tables["locations"]
    if config.location_ids:
        locations = locations[locations.location_id.isin(config.location_ids)]
    if len(times) * len(locations) > config.max_grid_rows:
        raise ValueError(
            "Grid exceeds configured row limit; build smaller date/location partitions"
        )
    if locations.empty:
        raise ValueError("No valid locations")
    pieces = []
    for location in locations.to_dict("records"):
        local = {}
        for name, table in tables.items():
            if "location_id" in table:
                local[name] = table[table.location_id == location["location_id"]]
            elif "campus_id" in table:
                local[name] = table[table.campus_id == location["campus_id"]]
            else:
                local[name] = table
        features = build_features(location, local, times, config)
        targets = build_targets(local, times, config)
        frame = features.join(targets)
        enough_quality = set(QUALITIES[: QUALITIES.index(config.minimum_quality) + 1])
        for horizon in config.horizons:
            shift = -(horizon // config.bucket_minutes)
            prefix = f"target_{horizon}m"
            frame[prefix] = targets.target_occupancy.shift(shift)
            frame[prefix + "_quality"] = targets.target_quality.shift(shift).fillna("D_UNKNOWN")
            frame[prefix + "_weight"] = targets.target_weight.shift(shift).fillna(
                config.target_weights[3]
            )
            frame[prefix + "_source"] = targets.target_source.shift(shift).fillna("unknown")
            frame[prefix + "_timestamp"] = frame.timestamp + pd.Timedelta(minutes=horizon)
            frame[f"eligible_{horizon}m"] = frame[prefix].notna() & frame[prefix + "_quality"].isin(
                enough_quality
            )
            if config.exclude_closed:
                frame[f"eligible_{horizon}m"] &= frame.is_open & frame.is_open.shift(
                    shift, fill_value=False
                )
            if config.required_features:
                frame[f"eligible_{horizon}m"] &= (
                    frame[list(config.required_features)].notna().all(axis=1)
                )
        frame = frame[(frame.timestamp >= start) & (frame.timestamp < end)].copy()
        count = frame.target_quality.isin(enough_quality).sum()
        frame["sparse_location"] = count < config.min_location_targets
        for horizon in config.horizons:
            frame[f"eligible_{horizon}m"] &= ~frame.sparse_location
        pieces.append(frame.reset_index(drop=True))
    frame = (
        pd.concat(pieces, ignore_index=True)
        .sort_values(["location_id", "timestamp"])
        .reset_index(drop=True)
    )
    timestamps = pd.DatetimeIndex(frame.timestamp.unique()).sort_values()
    if len(timestamps) < 3:
        raise ValueError("At least three buckets are required for chronological splits")
    train_end = (
        utc(config.train_end)
        if config.train_end
        else timestamps[
            max(1, min(len(timestamps) - 2, int(len(timestamps) * config.train_fraction)))
        ]
    )
    validation_end = (
        utc(config.validation_end)
        if config.validation_end
        else timestamps[
            max(
                2,
                min(
                    len(timestamps) - 1,
                    int(len(timestamps) * (config.train_fraction + config.validation_fraction)),
                ),
            )
        ]
    )
    frame["split"] = "train"
    frame.loc[frame.timestamp >= train_end, "split"] = "validation"
    frame.loc[frame.timestamp >= validation_end, "split"] = "test"
    for horizon in config.horizons:
        # Purge labels at/crossing the next split boundary; no overlapping training labels.
        label_time = frame[f"target_{horizon}m_timestamp"]
        allowed = (
            ((frame.split == "train") & (label_time < train_end))
            | ((frame.split == "validation") & (label_time < validation_end))
            | ((frame.split == "test") & (label_time < end))
        )
        frame[f"eligible_{horizon}m"] &= allowed
    frame["is_training_eligible"] = frame[[f"eligible_{h}m" for h in config.horizons]].any(axis=1)
    frame["sample_weight"] = frame[f"target_{config.horizons[0]}m_weight"]
    frame["location_holdout"] = frame.location_id.isin(config.holdout_locations)
    frame["feature_max_available_at"] = pd.to_datetime(frame.feature_max_available_at, utc=True)
    validate_frame(frame, config)
    report = quality_report(frame, cleaning, tables, config)
    report["split_boundaries"] = {
        "train_end": train_end.isoformat(),
        "validation_end": validation_end.isoformat(),
    }
    return frame, report


def build_dataset(snapshot, root, version, config, allow_synthetic=False):
    started = time.monotonic()
    version = safe_version(version)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"studyspot_occupancy_{version}"
    if destination.exists():
        raise FileExistsError(f"Dataset already exists: {destination}")
    raw, metadata = read_snapshot(snapshot)
    if metadata["synthetic"] and not allow_synthetic:
        raise ValueError("Synthetic source requires explicit --allow-synthetic")
    logger.info("Source counts: %s", {k: len(v) for k, v in raw.items()})
    frame, report = build_frame(raw, config)
    # Exclusive lock stops two builders from publishing the same version concurrently.
    lock = root / f".{destination.name}.lock"
    lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(lock_fd)
    staging = Path(tempfile.mkdtemp(prefix=".building-", dir=root))
    try:
        write_snapshot(staging / "source_snapshot", raw, metadata)
        frame.to_parquet(staging / "dataset.parquet", index=False)
        registry = feature_registry(config)
        manifest = {
            "dataset_version": version,
            "generated_at": datetime.now(UTC).isoformat(),
            "pipeline_version": PIPELINE_VERSION,
            "schema_version": SCHEMA_VERSION,
            "synthetic": metadata["synthetic"],
            "configuration": config.to_dict(),
            "source_row_counts": {k: len(v) for k, v in raw.items()},
            "source_snapshot_sha256": checksum(staging / "source_snapshot" / "snapshot.json"),
            "rows": len(frame),
            "locations": frame.location_id.nunique(),
            "feature_registry": registry,
            "schema": {k: str(v) for k, v in frame.dtypes.items()},
            "target_definition": "Per-location as-of label at T+h; trusted exact manual > consensus > weak > unknown. Bounded past tolerance; no nearest future bucket.",
            "split_boundaries": report["split_boundaries"],
            "files": {},
        }
        (staging / "quality.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
        (staging / "quality.md").write_text(summary(report, version, metadata["synthetic"]))
        for filename in ("dataset.parquet", "quality.json", "quality.md"):
            manifest["files"][filename] = checksum(staging / filename)
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
        if destination.exists():
            raise FileExistsError(f"Dataset already exists: {destination}")
        # Same-filesystem rename publishes a complete version atomically.
        staging.rename(destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        lock.unlink(missing_ok=True)
    logger.info(
        "Built %s rows in %.2fs at %s; cleaning=%s",
        len(frame),
        time.monotonic() - started,
        destination,
        report["cleaning"],
    )
    return destination, report


def summary(report, version, synthetic):
    return (
        f"# StudySpot dataset {version}\n\nSynthetic: {synthetic}\n\n"
        f"Rows: {report['rows']} | Locations: {report['locations']} | Eligible: {report['training_eligible']}\n\n"
        f"Range: {report['start']} to {report['end']}\n\n"
        f"Splits: {report['coverage']['split']}\n\nTarget quality: {report['coverage']['target_quality']}\n\n"
        f"Warnings: {report['warnings']}\n\nSchema, privacy, alignment and leakage validation: PASSED.\n"
    )


def validate_dataset(path, replay=False):
    path = Path(path)
    manifest = json.loads((path / "manifest.json").read_text())
    if (
        manifest["schema_version"] != SCHEMA_VERSION
        or manifest["pipeline_version"] != PIPELINE_VERSION
    ):
        raise ValueError("Unsupported dataset/pipeline version")
    if set(manifest["files"]) != {"dataset.parquet", "quality.json", "quality.md"}:
        raise ValueError("Invalid dataset file manifest")
    for name, digest in manifest["files"].items():
        if checksum(path / name) != digest:
            raise ValueError(f"Artifact checksum mismatch: {name}")
    if checksum(path / "source_snapshot" / "snapshot.json") != manifest["source_snapshot_sha256"]:
        raise ValueError("Source manifest checksum mismatch")
    raw, source = read_snapshot(path / "source_snapshot")
    if source["synthetic"] != manifest["synthetic"]:
        raise ValueError("Synthetic provenance mismatch")
    config = PipelineConfig(**manifest["configuration"])
    if manifest["feature_registry"] != feature_registry(config):
        raise ValueError("Feature registry mismatch")
    frame = pd.read_parquet(path / "dataset.parquet")
    checks = validate_frame(frame, config)
    if manifest["rows"] != len(frame) or manifest["schema"] != {
        k: str(v) for k, v in frame.dtypes.items()
    }:
        raise ValueError("Manifest schema/count mismatch")
    if replay:
        rebuilt, _ = build_frame(raw, config)
        pd.testing.assert_frame_equal(frame, rebuilt, check_dtype=False)
        checks["source_replay"] = "passed"
    return frame, manifest, checks


def load_dataset(
    version, root="ml/data/processed", horizon=60, allow_synthetic=False, holdout=False
):
    """Return {train/validation/test: {X, y, weights, keys}}, with no target columns in X."""
    path = Path(root) / f"studyspot_occupancy_{safe_version(version)}"
    frame, manifest, _ = validate_dataset(path)
    if manifest["synthetic"] and not allow_synthetic:
        raise ValueError("Synthetic dataset requires explicit opt-in")
    if horizon not in manifest["configuration"]["horizons"]:
        raise ValueError("Horizon not present")
    output = {}
    for split in ("train", "validation", "test"):
        part = frame[(frame.split == split) & frame[f"eligible_{horizon}m"]]
        if holdout:
            part = part[part.location_holdout if split == "test" else ~part.location_holdout]
        output[split] = {
            "X": part[list(manifest["feature_registry"])].reset_index(drop=True),
            "y": part[f"target_{horizon}m"].reset_index(drop=True),
            "weights": part[f"target_{horizon}m_weight"].reset_index(drop=True),
            "keys": part[["location_id", "timestamp"]].reset_index(drop=True),
        }
    return output
