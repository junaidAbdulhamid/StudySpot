import argparse
import json
from pathlib import Path

from ml.src.datasets import validate_dataset


def main():
    parser = argparse.ArgumentParser(
        description="Validate artifacts, schema, privacy, splits and replay from source"
    )
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    frame, _, checks = validate_dataset(args.dataset, replay=True)
    print(json.dumps(dict(checks, rows=len(frame)), indent=2))


if __name__ == "__main__":
    main()
