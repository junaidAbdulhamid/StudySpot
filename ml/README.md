# StudySpot historical data pipeline

Phase 6 turns operational PostgreSQL events into versioned, validated 15-minute Parquet rows. It does not train or serve a model. See [the pipeline guide](../docs/ml-data-pipeline.md) and [feature registry](../docs/ml-feature-registry.md).

From the repository root:

```sh
UV_CACHE_DIR=/private/tmp/studyspot-uv-cache uv sync --project ml
ml/.venv/bin/python -m ml.scripts.generate_synthetic_history --start 2026-09-01T00:00:00Z --days 7 --locations 3 --seed 42 --output ml/data/raw/dev_v001
ml/.venv/bin/python -m ml.scripts.build_dataset --start 2026-09-01 --end 2026-09-08 --version dev_v001 --snapshot ml/data/raw/dev_v001 --allow-synthetic
ml/.venv/bin/python -m ml.scripts.validate_dataset --dataset ml/data/processed/studyspot_occupancy_dev_v001
ml/.venv/bin/python -m ml.scripts.inspect_dataset --dataset ml/data/processed/studyspot_occupancy_dev_v001
ml/.venv/bin/pytest ml/tests -q
ml/.venv/bin/ruff check ml
```

For a database build, omit `--snapshot` and `--allow-synthetic`, set `DATABASE_URL` (or use `backend/.env`), and give a fresh version. Extraction is read only, bounded by time and selected locations. `--location-id` may be repeated; `--calendar` and `--weather` accept optional CSV imports. A bare date means midnight UTC; full timestamps need an offset. Version directories and their source snapshots are immutable and ignored by Git. Retain production artifacts externally.

Phase 7 uses this contract:

```python
from ml.src.datasets import load_dataset

splits = load_dataset("v001", horizon=60)
X_train = splits["train"]["X"]
y_train = splits["train"]["y"]
weights_train = splits["train"]["weights"]
```

Synthetic datasets require `allow_synthetic=True` on load. `keys` contains location/time metadata. `X` includes only registered features and no target columns.
