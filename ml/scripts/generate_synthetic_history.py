import argparse
import json
from pathlib import Path

from ml.src.snapshot import checksum, write_snapshot
from ml.src.synthetic import generate_history


def main():
    parser = argparse.ArgumentParser(
        description="Generate explicitly synthetic development history"
    )
    parser.add_argument("--start", default="2026-09-01T00:00:00Z")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--locations", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frames, metadata, truth = generate_history(args.start, args.days, args.locations, args.seed)
    write_snapshot(args.output, frames, metadata)
    # Diagnostic truth is separate, never selected as a feature or loaded by the pipeline.
    truth_path = args.output / "synthetic_truth.parquet"
    truth.to_parquet(truth_path, index=False)
    (args.output / "synthetic_truth.json").write_text(
        json.dumps(
            {
                "synthetic": True,
                "sha256": checksum(truth_path),
                "purpose": "Development diagnostics only; not a model feature",
            },
            indent=2,
        )
    )
    print(f"SYNTHETIC history: {args.output}; {len(truth)} location/time points")


if __name__ == "__main__":
    main()
