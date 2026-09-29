import argparse
import logging
import os
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from ml.src.config import PipelineConfig
from ml.src.datasets import build_dataset, summary
from ml.src.extraction import extract_database
from ml.src.snapshot import safe_version, write_snapshot


def main():
    parser = argparse.ArgumentParser(description="Build a versioned StudySpot occupancy dataset")
    parser.add_argument("--start", required=True, help="ISO timestamp with offset")
    parser.add_argument("--end", required=True, help="Exclusive ISO timestamp with offset")
    parser.add_argument("--version", required=True)
    parser.add_argument("--config", type=Path, default=Path("ml/config/default.json"))
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("ml/data/processed"))
    parser.add_argument("--raw-root", type=Path, default=Path("ml/data/raw"))
    parser.add_argument("--location-id", action="append")
    parser.add_argument(
        "--calendar",
        type=Path,
        help="CSV: date,campus_id,academic_period,is_class_day,is_exam_period,is_holiday,available_at",
    )
    parser.add_argument(
        "--weather",
        type=Path,
        help="CSV: campus_id,observed_at,available_at,temperature_c,precipitation_mm",
    )
    parser.add_argument("--allow-synthetic", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    def instant(value):
        # A bare date means midnight UTC; full timestamps must include a timezone offset.
        return f"{value}T00:00:00Z" if len(value) == 10 and date.fromisoformat(value) else value

    config = PipelineConfig.from_file(
        args.config, start=instant(args.start), end=instant(args.end), location_ids=args.location_id
    )
    snapshot = args.snapshot
    if snapshot and (args.calendar or args.weather):
        parser.error("Imports belong to extraction; an existing snapshot is immutable")
    if not snapshot:
        load_dotenv("backend/.env", override=False)
        url = os.environ.get("DATABASE_URL")
        if not url:
            parser.error("Set DATABASE_URL or provide --snapshot")
        raw, metadata = extract_database(url, config)
        for name in ("calendar", "weather"):
            path = getattr(args, name)
            if path:
                raw[name] = pd.read_csv(path)
        snapshot = args.raw_root / safe_version(args.version)
        write_snapshot(snapshot, raw, metadata)
    destination, report = build_dataset(
        snapshot, args.output_root, args.version, config, args.allow_synthetic
    )
    print(
        summary(
            report,
            args.version,
            __import__("json").loads((destination / "manifest.json").read_text())["synthetic"],
        )
    )
    print(f"Dataset: {destination}")


if __name__ == "__main__":
    main()
