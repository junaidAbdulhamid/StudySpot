# Phase 6 feature registry

`ml/src/registry.py` is the machine-readable source of truth. Each manifest embeds its entries: type, source, meaning, inference availability and leakage rule. **Known** means both event time and knowledge time are no later than row time T. Nullable values stay null; counts are zero when no events are known. Targets and `feature_max_available_at` are metadata, not features.

| Feature(s) | Source | Type / range | Definition and leakage control |
| --- | --- | --- | --- |
| `occupancy_now` | OccupancyEstimate | float 0–100, nullable | Latest known non-seed estimate within configured age. |
| `current_confidence_score` | OccupancyEstimate | float 0–1, nullable | Historical estimate confidence decayed from event time. |
| `recent_signal_count`, `signal_age_seconds` | OccupancyEstimate | nonnegative numbers | Saved signal count (zero if none) and selected estimate age (null if none). |
| `occupancy_lag_{15,30,60,120}m` and `_missing` | OccupancyEstimate | float 0–100 / bool | Reconstructed `occupancy_now` exactly N buckets ago for the same location. |
| `occupancy_rolling_mean_{30,60,120}m`, `_std_`, `_count_` | OccupancyEstimate | numbers | Known snapshots in `(T-window,T]`; skips missing values and exports count. |
| `occupancy_trend_60m` | OccupancyEstimate | float -100–100 | Current known occupancy minus exact 60-minute lag. |
| `report_count_{15,30,60}m` | CrowdReport | integer ≥0 | Known reports in `(T-window,T]`. |
| `mean_report_value_30m`, `weighted_report_value_30m`, `report_std_30m` | CrowdReport | float, nullable | Mean, submission-reliability weighted mean, population standard deviation of known 30-minute values. |
| `verified_report_fraction_30m`, `mean_report_reliability_30m` | CrowdReport | float 0–1, nullable | Known 30-minute verified share and reliability captured at submission; no identity. |
| `active_checkins` | CheckIn | integer ≥0 | Known starts minus known checkout or scheduled expiry; never physical headcount. |
| `checkins_started_{15,30}m`, `checkouts_{15,30}m`, `net_checkin_change_30m` | CheckIn | integer | Known starts/checkouts in `(T-window,T]`; net is starts minus checkouts. |
| `validations_{accurate,more_crowded,less_crowded}_30m`, `validation_agreement_rate` | OccupancyValidation | integer / float 0–1 | Known 30-minute category counts and accurate share; null share for no validations. |
| `capacity`, `noise_level`, `floor`, `building_id`, `campus_id` | StudyLocation / Building / Campus | number / categorical | Current metadata only after `available_at`; historical edits need versioning. |
| `hour_of_day`, `minute_of_hour`, `day_of_week`, `is_weekend`, `month`, `week_of_year` | Campus.timezone | integers / bool | Local wall time; Monday=0; ISO week; IANA timezone. |
| `sin_hour`, `cos_hour`, `sin_day`, `cos_day` | Campus.timezone | float -1–1 | Cyclic local hour and weekday encodings. |
| `is_open`, `minutes_since_open`, `minutes_until_close` | StudyLocation hours, Campus.timezone | bool / minutes | Local opening interval, including overnight and DST; offsets null when closed or metadata unknown. |
| `academic_period`, `is_exam_period`, `is_class_day`, `is_holiday` | Optional calendar CSV | string / nullable bool | Campus/local date join only if published by T; unknown period is `UNKNOWN`. |
| `temperature_c`, `precipitation_mm` | Optional weather CSV | floats, nullable | Latest weather observed and known by T, age ≤60 minutes; no future actuals. |
| `metadata_missing`, `occupancy_missing`, `weather_missing`, `calendar_missing`, `occupancy_lag_*_missing` | Pipeline | bool | Explicit absence flags. |

All listed features can be supplied at inference if their source is present; optional imports can remain absent. The registry is an allowlist: validation fails if a new feature column is not explicitly registered.
