# Forecasting boundary

Reserved for a later phase. No model is trained, served, or called here.

Phase 2 persists occupancy forecasts in `occupancy_predictions`, but every row the seed writes is
`source = 'seed'` with `model_version = 'seed-v1'` — development demo values, not predictions. The
`/api/v1/locations/{id}/predictions` endpoint and the mobile predictions screen read whatever is
persisted, so Phase 7 can write real rows with a real `model_version` and the UI needs no change.

`occupancy_observations` is the table intended to hold ground truth for training; Phase 5's crowd
reports and check-ins are what will start filling it.

Recommendation ranking is not ML either: it is deterministic scoring in
`mobile/utils/recommendations.ts`.
