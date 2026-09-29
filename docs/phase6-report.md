# Phase 6 completion report — historical occupancy data

Phase 6 is implemented in the working tree. It creates ML-ready, versioned datasets from operational occupancy events without training a forecasting model. The data layer lives in `ml/`; [pipeline behavior and limitations](ml-data-pipeline.md) and the [complete feature registry](ml-feature-registry.md) are documented separately.

## Architecture and source contract

`extraction.py` reads the actual Phase 5 tables `occupancy_estimates`, `occupancy_observations`, `crowd_reports`, `checkins`, and `occupancy_validations`, plus `study_locations`, `buildings`, and `campuses`. It uses a bounded time interval, optional location IDs, chunks, and a read-only repeatable-read transaction. Optional campus academic calendar and weather CSVs enter the same snapshot. Extraction excludes users and account fields. `snapshot.py` stores raw-but-allowlisted Parquet tables with SHA-256 checksums. `cleaning.py` normalizes UTC timestamps and rejects invalid ranges, seat counts, chronology and duplicate/conflicting IDs. `features.py` and `targets.py` calculate location-local series. `datasets.py` joins them, produces future labels, chronological splits, and immutable versioned Parquet. `validation.py` checks ranges, schema, privacy, uniqueness, time alignment and split integrity. `registry.py` provides a machine-readable feature allowlist; Phase 7 reads it from the manifest.

The canonical grain is **location × 15-minute UTC bucket start**, configurable in `PipelineConfig`. Report/check-in/validation windows use `(T-window,T]`. Campus-local hour, weekday, opening hours, overnight periods and DST use the campus IANA timezone. Features use events whose event time **and** recorded/knowledge time are at or before T. Historical occupancy uses the historical estimate known by T, never the current API's latest value. Observation labels may use late-entered ground truth; features cannot. Checkouts do not appear before their recorded time. Features are grouped by location and rows sorted before lag/rolling calculations. `feature_max_available_at <= timestamp` is a fatal validation rule. Location metadata has no history table; the current row is hidden until its `updated_at` and older versions cannot be reconstructed.

## Targets and schema

Tier A uses a recent trusted manual observation with exact valid occupied/total seat counts (`occupied / total × 100`, weight 1.0). Tier B uses a recent non-seed estimate backed by at least 3 known reports, confidence ≥0.7 after decay, report standard deviation ≤15, and verified fraction ≥0.6 (weight 0.75). Tier C is a valid recent non-seed estimate failing B criteria (weight 0.35). Tier D has no defensible value, weight 0 and no target. These thresholds and the minimum accepted tier are configurable. Target source and quality accompany every value. Forecast horizons are **15, 30, 60 and 120 minutes**; each has its own target, quality, weight, source, exact target timestamp and eligibility. The target builder uses only observations/estimates no later than the target timestamp and bounded staleness, never an arbitrary nearest future sample.

The processed schema has `location_id`, UTC `timestamp`, 68 registered features, `target_occupancy` and its quality/source/weight, horizon-specific target fields, `sample_weight`, `split`, sparse/holdout/eligibility flags, and a knowledge-time audit timestamp. Features include historical occupancy, exact lags, rolling means/std/counts and trend; report counts/weighted values/dispersion/verification; check-in starts/checkouts/active count; validation counts/agreement; confidence and signal age; static location fields; local time/cyclic encodings; operating-hour offsets; optional academic/weather fields; and missing indicators. Raw user IDs, email, display names, auth IDs, tokens and GPS histories are absent. `sample_weight` reflects the first configured horizon for general inspection; Phase 7 should use the selected horizon's `target_{h}m_weight` via `load_dataset`.

Train/validation/test use ordered global UTC boundaries (default 70/15/15), with explicit boundary overrides. Labels crossing a split boundary are ineligible. A location with fewer than the configured minimum valid target rows is flagged sparse and excluded from training. Closed periods are retained for analysis but ineligible by default. Optional held-out locations support unseen-location evaluation alongside temporal splits. `quality.json`/`.md` include tier, missingness, invalid-row, occupancy-band, signal, location, weekday/hour/date/month/academic-period, horizon and split coverage, with warnings distinct from fatal checks.

Each dataset version directory holds the Parquet data, a frozen source snapshot, checksummed manifest, machine-readable quality report and readable quality summary. Existing versions cannot be silently overwritten. Local files are ignored by Git; move/copy version directories to durable storage for production. Dataset ingestion can be repeated by bounded date/location partitions with new versions. A seeded development generator creates irregular reports, visits, observations, location patterns, weekend/exam/holiday effects, noise, spikes, conflicts and deliberately invalid examples. Its diagnostic `true_occupancy` stays in a separate synthetic-only file and is never a model feature. Synthetic builds and loads require explicit opt-in.

## Actual validation and generated data

Executed on 2026-09-29: `uv sync --project ml`; `ml/.venv/bin/ruff check ml`; `ml/.venv/bin/ruff format --check ml`; `ml/.venv/bin/pytest ml/tests -q --disable-warnings`; synthetic generator, builder, validator and inspector CLIs; and a read-only extraction plus complete build from the local development PostgreSQL database. The test suite covers bucketing, target tiers and alignment, event vs knowledge time across source types, cross-location lag isolation, rolling arithmetic, DST/overnight hours, cleaning, privacy, split chronology, artifact immutability and source replay. The synthetic artifact `studyspot_occupancy_phase6_dev_v2` contains **576 rows at two locations, 68 features, 420 eligible rows**, tier A 236 / B 4 / C 336, 402 train / 86 validation / 88 test rows. Five invalid synthetic report values were removed. Validation and source replay passed; weather remains intentionally absent. The local database artifact `studyspot_occupancy_phase6_local_live` contains **1,152 rows at 12 locations and zero eligible rows**, because its selected date has no live crowd reports/check-ins/validations or trusted exact observations; the existing estimates/observations are development seed data. A zero-eligible report is expected and honest, not a model-ready real corpus.

Exact real-data command from repository root, after setting `DATABASE_URL` or `backend/.env`:

```sh
ml/.venv/bin/python -m ml.scripts.build_dataset --start 2026-09-01 --end 2026-10-01 --version v001
ml/.venv/bin/python -m ml.scripts.validate_dataset --dataset ml/data/processed/studyspot_occupancy_v001
```

Phase 7 contract:

```python
from ml.src.datasets import load_dataset
data = load_dataset("v001", horizon=60)
X_train, y_train, weights_train = data["train"]["X"], data["train"]["y"], data["train"]["weights"]
X_val, y_val, weights_val = data["validation"]["X"], data["validation"]["y"], data["validation"]["weights"]
X_test, y_test, weights_test = data["test"]["X"], data["test"]["y"], data["test"]["weights"]
```

Known limits: real historical contribution coverage is still sparse; crowd-derived Tier B/C values are pseudo ground truth, and their weights require evaluation. Actual operating-hour changes and strict transaction commit knowledge time require CDC/versioned metadata for perfect historical reconstruction. The optional weather import represents weather known at T; Phase 7 must use forecast-issued weather for future horizon covariates. No model training, prediction endpoint or orchestration service was added.
