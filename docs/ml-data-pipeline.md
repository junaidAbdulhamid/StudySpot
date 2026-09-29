# Phase 6 historical occupancy data

The pipeline extracts `OccupancyEstimate`, `OccupancyObservation`, `CrowdReport`, `CheckIn`, and `OccupancyValidation`, plus location/building/campus metadata, in a read-only, repeatable-read PostgreSQL transaction. Queries have a time bound and optional location IDs. Extraction omits users, email, auth IDs, device coordinates, and tokens. Raw snapshots contain opaque event IDs for deduplication; processed rows contain no event or user ID.

`ml/src/extraction.py` selects data → `snapshot.py` writes a checksummed Parquet source snapshot → `cleaning.py` removes invalid records → `features.py` and `targets.py` reconstruct location series → `datasets.py` aligns future labels and chronological splits → `validation.py` checks schema, privacy, ranges, uniqueness, time, boundaries and artifact replay. Each version has `dataset.parquet`, `manifest.json`, `quality.json`, `quality.md`, and `source_snapshot/`. The manifest saves config, schema, source counts, checksums, pipeline/schema versions, range, split boundaries, feature registry, target definition and synthetic status. Rerunning a version fails. Rebuilding from its embedded snapshot permits deterministic replay; `generated_at` is intentionally variable.

Run from the repository root after `uv sync --project ml`:

```sh
ml/.venv/bin/python -m ml.scripts.build_dataset --start 2026-09-01 --end 2026-10-01 --version v001
ml/.venv/bin/python -m ml.scripts.validate_dataset --dataset ml/data/processed/studyspot_occupancy_v001
ml/.venv/bin/python -m ml.scripts.inspect_dataset --dataset ml/data/processed/studyspot_occupancy_v001
```

The build reads `DATABASE_URL` from the environment or `backend/.env`. Dates mean midnight UTC; full timestamps require an offset. `--config ml/config/default.json` and repeated `--location-id` customize a run. `--snapshot` builds from a frozen extraction; use fresh versions for incremental date partitions. A configurable grid limit bounds work. No scheduler or object storage is installed yet; directories can be copied to object storage without changing the format.

## Grain, time and labels

Each row is one location at one UTC bucket start T, normally every 15 minutes. Raw event aggregation uses `(T-window, T]`; a report at 14:02 enters 14:15, never 14:00. Features use only information known at or before T. Campus-local time and opening hours use the IANA timezone on `Campus`, including DST. An overnight location's opening belongs to the previous local date before closing. Closed rows are visible for coverage but ineligible by default.

Labels correspond to exactly T+15, T+30, T+60 and T+120 minutes. A target uses the latest observation/estimate at or before its target time, within its configured maximum age (15 minutes for observations, 30 for estimates); it never chooses a later event. Future ground truth is allowed for a label. Missing or invalid evidence yields null and `D_UNKNOWN`. Each horizon has its own quality, source, weight, timestamp and eligibility.

| Tier | Requirement | Default weight |
| --- | --- | ---: |
| A_TRUSTED | Recent `manual` exact observation with `total_seats > 0` and `0 <= occupied_seats <= total_seats`; percentage computed from counts | 1.00 |
| B_STRONG_CONSENSUS | Non-seed estimate and at least 3 known reports in its preceding 30 minutes, decayed confidence ≥ .70, report standard deviation ≤ 15 points, verified fraction ≥ .60 | .75 |
| C_WEAK_ESTIMATE | Recent non-seed estimate with valid percentage that misses B criteria | .35 |
| D_UNKNOWN | No valid evidence | 0; excluded |

Manual exact counts have priority. Defaults are configurable hypotheses saved in each manifest. Crowd pseudo labels can be biased and should be evaluated separately from Tier A. Check-in counts are contribution signals, never physical headcount.

## Knowledge time and leakage

For estimates, reports, validations and observations, knowledge time is the later of event time and `created_at`. For checkout it is the latest of checkout event time, `updated_at`, and `created_at`. Scheduled check-in expiry is known at check-in time. A 13:55 report recorded at 14:10 cannot enter the 14:00 feature row. A manual observation at 14:00 entered at 14:20 can label 14:00 but cannot inform 14:00 features. `occupancy_now` comes from the historical non-seed estimate known at T. Lags and rolling values use that same reconstructed series, grouped by location. `feature_max_available_at` is checked against T. Tests cover late reports, estimates, checkouts, validations, horizons, DST and cross-location isolation.

Operational `created_at`/`updated_at` are database timestamps, not immutable commit-time CDC. The app has no location metadata history. The pipeline conservatively hides current capacity/hours until current metadata `updated_at`; to reconstruct older edits accurately, add versioned metadata or CDC. A snapshot preserves the database at extraction, but cannot recover records deleted before extraction. Strict commit-time availability under concurrent transactions also needs CDC or commit sequence.

## Features and optional imports

The [registry](ml-feature-registry.md) documents every feature. Counts become zero when no events exist; occupancy, moments, lags, calendar and weather stay null or `UNKNOWN`. Missing flags are exported. Invalid percentages, seat counts, capacity, reliability/confidence, chronology and duplicate/conflicting IDs are rejected or fail the build; aggregate removal counts appear in `quality.json`.

Pass `--calendar` a CSV with `date,campus_id,academic_period,is_class_day,is_exam_period,is_holiday,available_at`. Periods are `REGULAR`, `MIDTERM`, `READING_DAY`, `FINAL_EXAM`, `BREAK`, `HOLIDAY`. `available_at` needs a UTC offset and represents publication time. Campus IDs must match PostgreSQL. No official GMU dates are bundled; import verified university calendar dates before relying on these features.

Optional `--weather` CSV columns: `campus_id,observed_at,available_at,temperature_c,precipitation_mm`. The latest known observation within 60 minutes is used. The pipeline works without weather. Future predictions must use forecasts issued by prediction time, not future actual weather; the current columns represent only current-at-T weather.

## Splits, quality and Phase 7

Default train/validation/test spans earliest 70% / next 15% / latest 15% of UTC buckets across all locations. Explicit `train_end` and `validation_end` are supported. A row whose target time crosses the next split boundary is ineligible. `min_location_targets` flags sparse locations. Optional `holdout_locations` enables unseen-location evaluation with `load_dataset(..., holdout=True)` alongside the temporal split. Eligibility requires a valid target at the chosen horizon, configured quality, open location at T and T+h, required features if configured, and sufficient location evidence.

`load_dataset(version="v001", horizon=60)` returns `train`, `validation`, `test`, each with `X`, `y`, `weights`, `keys`. `X` contains only registry features, never targets or split metadata. Phase 7 can compute last-value, local hour/day historical mean and rolling-mean baselines. Synthetic loads require `allow_synthetic=True`. `quality.json` has source/removal counts, tier/horizon coverage, missingness, location/date/hour/day/month/period distributions, report verification, target occupancy bands, warnings and split counts. Warnings such as sparse locations or absent Tier A do not suppress fatal validation errors.

`python -m ml.scripts.generate_synthetic_history --days 7 --locations 3 --seed 42 --output ml/data/raw/dev_v001` makes labeled synthetic source and separate `synthetic_truth.parquet` diagnostics. It varies time of day, weekends, exams, holidays, locations, contribution adoption, noise, conflicts, missing reports, spikes and invalid values. True occupancy is never a processed feature. Synthetic builds and loads require explicit opt-in and do not establish real campus accuracy.

Real crowd history is currently sparse. Most real locations may have no eligible rows until trusted exact counts or live estimates accumulate. Predictive performance and tier weights are Phase 7 questions; no model training or serving happens here.
