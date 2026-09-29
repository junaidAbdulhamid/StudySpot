import argparse
import json
from pathlib import Path

from ml.src.datasets import validate_dataset


def main():
    parser = argparse.ArgumentParser(description="Inspect dataset coverage and optional CSV export")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    frame, manifest, checks = validate_dataset(args.dataset)
    report = json.loads((args.dataset / "quality.json").read_text())
    print(
        json.dumps(
            {
                "rows": len(frame),
                "locations": frame.location_id.nunique(),
                "features": len(manifest["feature_registry"]),
                "synthetic": manifest["synthetic"],
                "horizons": report["horizons"],
                "top_missing": sorted(report["missingness"].items(), key=lambda x: -x[1])[:10],
                "checks": checks,
            },
            indent=2,
        )
    )
    if args.csv:
        if args.csv.exists():
            raise FileExistsError(args.csv)
        frame.to_csv(args.csv, index=False)


if __name__ == "__main__":
    main()
