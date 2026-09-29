"""Immutable local artifacts, checksums, and privacy allowlists."""

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from ml.src.extraction import SOURCES

ALLOWED = {name: set(columns) for name, (_, _, columns) in SOURCES.items()}
ALLOWED.update(
    {
        "locations": {
            "location_id",
            "capacity",
            "noise_level",
            "floor",
            "opening_time",
            "closing_time",
            "is_active",
            "building_id",
            "campus_id",
            "timezone",
            "available_at",
        },
        "calendar": {
            "date",
            "campus_id",
            "academic_period",
            "is_class_day",
            "is_exam_period",
            "is_holiday",
            "available_at",
        },
        "weather": {
            "campus_id",
            "observed_at",
            "available_at",
            "temperature_c",
            "precipitation_mm",
        },
    }
)


def checksum(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def safe_version(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        raise ValueError("Version must be a simple name, not a path")
    return value


def check_source_columns(tables):
    if set(tables) != set(ALLOWED):
        raise ValueError("Unexpected or missing snapshot tables")
    for name, frame in tables.items():
        extra = set(frame.columns) - ALLOWED[name]
        if extra:
            raise ValueError(f"Prohibited/unexpected source columns in {name}: {sorted(extra)}")
        if name in SOURCES and not set(SOURCES[name][2]) <= set(frame.columns):
            raise ValueError(f"Missing source schema: {name}")


def write_snapshot(path, tables, metadata):
    check_source_columns(tables)
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    files = {}
    for name, frame in tables.items():
        target = path / f"{name}.parquet"
        frame.to_parquet(target, index=False)
        files[target.name] = checksum(target)
    manifest = dict(metadata, files=files, row_counts={k: len(v) for k, v in tables.items()})
    (path / "snapshot.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    return manifest


def read_snapshot(path):
    path = Path(path)
    metadata = json.loads((path / "snapshot.json").read_text())
    expected = {f"{name}.parquet" for name in ALLOWED}
    if set(metadata["files"]) != expected or not isinstance(metadata.get("synthetic"), bool):
        raise ValueError("Invalid snapshot manifest")
    for name, digest in metadata["files"].items():
        if checksum(path / name) != digest:
            raise ValueError(f"Snapshot checksum mismatch: {name}")
    tables = {name: pd.read_parquet(path / f"{name}.parquet") for name in ALLOWED}
    check_source_columns(tables)
    return tables, metadata
