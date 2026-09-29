# Phase 5 occupancy system

StudySpot does not count everyone in a room. Current occupancy is an estimate from student reports and, when available, trusted manual observations. An empty signal window returns **unknown**. The old seed records are excluded from current occupancy; forecasts and historical charts remain labeled examples.

## Signals and estimator

- A report asks for a broad category. Internal representative values are lots of seats = 20, moderate = 50, busy = 75, and nearly full = 92. These numbers are modeling assumptions.
- Reports up to two hours old receive a weight of `2^(-age_minutes / REPORT_HALF_LIFE_MINUTES)` (25 minutes by default), multiplied by a bounded reliability factor `0.6 + 0.8 × clamp(score, 0.2, 1)` and a proximity factor of 1.25 if within `CHECKIN_RADIUS_METERS` or 0.8 otherwise. The weighted median resists a single outlier.
- A trusted manual observation from the past hour supplies a strong anchor (65% manual, 35% reports where both exist). Students cannot submit exact seat counts. Without reports or a recent trusted observation, check-ins and validations alone cannot create a percentage.
- Check-ins raise confidence modestly, at most 0.07; they never translate directly into physical occupancy. There is no calibrated adoption rate. Validations affect confidence, not the percentage. No machine learning or fabricated headcount is used.
- Confidence is computed separately: `min(0.7, report_weight/(report_weight+3)) × agreement`, with agreement based on weighted absolute deviation from the median. Check-ins add at most 0.07, accurate validations at most 0.12, disagreement subtracts at most 0.20. A recent manual observation sets a floor of 0.75. Read-time confidence then decays with a 45-minute half-life. Scores below 0.40 are low, below 0.70 medium, otherwise high. Estimates older than `OCCUPANCY_MAX_AGE_MINUTES` (90 by default) become unknown. Confidence is not a statistical probability.
- Reliability starts at 0.5 and stays internal. Once at least three distinct users provide recent reports and the aggregate reaches medium confidence, each unassessed report receives at most +0.01 for agreement within 20 points or -0.01 for disagreement of 40+ points, clamped to 0.2–1.0. This is a conservative consistency signal, not a public reputation score.

## Durable events and cache

PostgreSQL holds check-ins, category reports, validations, trusted observations and estimate snapshots. New tables, indexes and snapshot signal summaries come from Alembic revisions `25630308138d`, `25630308138e` and `25630308138f`. One active check-in per user is enforced with a partial unique index; checking into another location completes the previous visit. A repeated check-in to the same active location returns the same record. Checkout is idempotent and only the owner can perform it. Active reads ignore expired visits even before cleanup runs.

Redis caches the current aggregate under `studyspot:occupancy:{location_id}` for 60 seconds and the report cooldown under `studyspot:ratelimit:report:{user_id}:{location_id}`. PostgreSQL remains authoritative. A cache failure falls back to the latest PostgreSQL snapshot. List and nearby APIs load current snapshots in a single bulk query rather than one request per card. Report cooldown is also checked under a user row lock against durable reports, so a Redis outage does not remove the limit.

Report and validation cooldowns default to ten minutes per user and location. Each check-in expires after four hours unless checked out. Run `.venv/bin/python -m app.jobs.expire_checkins` every minute with an external scheduler (for example cron or a job runner). This job marks expired rows and recomputes affected locations; the API's active-count query also excludes overdue rows. A production deployment must schedule the job externally rather than rely on a FastAPI worker timer.

## Location, privacy and limitations

Coordinates are optional. The server computes PostGIS distance to the study zone, stores only a proximity result and approximate distance for check-ins, and does not store the raw coordinates. Client-supplied GPS is an abuse-reduction signal, not proof of presence or indoor floor. Check-ins without GPS remain possible and reports have lower estimator weight without proximity verification. Ordinary student endpoints show only aggregate occupancy and the caller's own check-in; reports and validation responses contain no other user's identity. Authentication derives the user from a verified bearer token. There is no student endpoint for trusted exact observations.

Current snapshots are recomputed after contributions, switches, checkout, and expiry cleanup. Frequent reads use Redis or the latest PostgreSQL snapshot. Future Phase 6 can consume event timestamps and estimate snapshots, while Phase 7 can train and evaluate models against trusted observations. Those pipelines are not implemented here. Cold starts, limited participation, GPS spoofing, agreement among biased reporters, and delayed scheduler runs remain limitations.

## Local operation

Start PostgreSQL and Redis with `docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml up -d db redis`. Set `REDIS_URL` in `backend/.env`, run `.venv/bin/alembic upgrade head`, seed the catalog, then start the API. Supabase authentication must be configured for normal sign-in. The isolated browser test fixture supplies local test identities only.

Call `POST /api/v1/checkins` with `{ "location_id": "zone-1" }`, `POST /api/v1/crowd-reports` with `{ "location_id": "zone-1", "crowd_level": "moderate" }`, and read `GET /api/v1/locations/zone-1/occupancy`. Mutation calls require the caller's bearer token. Optional `latitude` and `longitude` must be supplied together. The response includes an estimate ID for `POST /api/v1/occupancy-validations`. Run the expiry command above from an external scheduler.
