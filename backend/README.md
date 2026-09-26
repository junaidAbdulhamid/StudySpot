# StudySpot API

FastAPI + SQLAlchemy 2 + PostgreSQL/PostGIS. This is Phase 2: the persistent campus data foundation
the Phase 1 mobile app now reads from. Authentication, live occupancy, crowd reporting, proximity
search, and forecasting models are later phases and are not implemented here.

## Layering

```text
FastAPI router (app/api/v1/*)      HTTP parameters, status codes, response models
  → service     (app/services/*)   orchestration, not-found policy, assembly
    → repository (app/repositories/*) queries, filters, persistence
      → SQLAlchemy models (app/models/entities.py)
        → PostgreSQL + PostGIS
```

Route handlers stay thin — they resolve dependencies and hand off. Business rules live in services;
every `SELECT` lives in a repository. Pydantic schemas (`app/schemas/catalog.py`) are the only thing
serialized; ORM instances never leave the service layer.

| Path | Contents |
| --- | --- |
| `app/main.py` | App factory, CORS, exception handlers, lifespan/logging, `/docs` and `/redoc` |
| `app/core/config.py` | `pydantic-settings` config, `.env`, validation of unsafe combinations |
| `app/core/database.py` | One cached engine with `pool_pre_ping`, session factory, `get_db` dependency |
| `app/core/exceptions.py` | `AppError` plus handlers that map everything to one error envelope |
| `app/core/logging.py` | JSON log formatter on the `studyspot` logger |
| `app/api/dependencies.py` | `Database` session dependency and the development-identity guards |
| `app/models/` | Declarative base with a naming convention, enums, all entities |
| `app/repositories/` | `Campus`, `Building`, `Location`, `Occupancy`, `Prediction`, `User`, `Favorite`, `Preference` |
| `app/services/` | `CampusService`, `BuildingService`, `LocationService`, `PredictionService`, `UserService`, `FavoriteService`, `PreferenceService` |
| `app/utils/occupancy.py` | `classify_occupancy()` — the single threshold definition |
| `app/seed/` | Idempotent development seed plus `phase1.json` exported from the Phase 1 dataset |
| `alembic/` | Migrations; `0001` is the whole Phase 2 schema |
| `tests/` | 49 pytest tests against a dedicated `_test` database |

Schema details, the ER diagram, constraints, indexes and seed counts are in
[../docs/database.md](../docs/database.md).

## Local setup

Requires Python 3.12+ and Docker (for PostGIS). [uv](https://docs.astral.sh/uv/) manages the
environment; `uv.lock` is committed.

```sh
# 1. Start PostgreSQL + PostGIS (from repository root)
cp infrastructure/.env.example infrastructure/.env     # then set POSTGRES_PASSWORD
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml up -d db

# 2. Configure and install
cd backend
cp .env.example .env                                   # same password in both URLs
uv sync --python 3.12

# 3. Create the schema and load development data
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed.run

# 4. Run
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

`http://127.0.0.1:8001/docs` and `/redoc` are served in development and test, and are disabled when
`APP_ENV=production`. Port 8001 (and database port 55432) were chosen to avoid colliding with other
local projects on 8000/5432; change them in `.env` if you prefer.

Re-run `.venv/bin/python -m app.seed.run` whenever the demo forecasts have gone stale — seeded
predictions only cover four hours from the moment they were written.

## Environment variables

`backend/.env`, never committed. See `.env.example`.

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_ENV` | `development` | `development` \| `test` \| `production` |
| `DEBUG` | `false` | Must be `false` when `APP_ENV=production` |
| `DATABASE_URL` | — | Required; must use the `postgresql+psycopg://` driver |
| `API_V1_PREFIX` | `/api/v1` | Leading slash, no trailing slash |
| `CORS_ORIGINS` | `[]` | JSON list of explicit origins; `*` is rejected |
| `DEV_USER_ENABLED` | `false` | Must be `false` when `APP_ENV=production` |
| `DEV_USER_ID` | `dev-studyspot` | The one identity the user-scoped routes accept |
| `TEST_DATABASE_URL` | — | Used by tests only; the database name must end in `_test` |

Credentials are held as `SecretStr`, the engine runs with `hide_parameters=True`, and the logger only
records exception types — no SQL, values, or configuration reaches the logs or the client.

## Endpoints

All under `API_V1_PREFIX`. Single resources return `{"data": {...}}`; collections return
`{"items": [...], "page": 1, "page_size": 20, "total": n}`.

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/health` | `{"status","database","postgis"}`; 503 if either is unreachable |
| GET | `/campuses` | Paginated |
| GET | `/campuses/{campus_id}` | |
| GET | `/buildings` | Optional `campus_id` |
| GET | `/buildings/{building_id}` | |
| GET | `/locations` | `search`, `campus_id`, `building_id`, `noise_level`, `amenities` (comma-separated slugs, all must match), `min_occupancy`, `max_occupancy`, `open_now`, `page`, `page_size` |
| GET | `/locations/{location_id}` | Location, building, campus, amenities, hours, latest estimate, forecasts, recent observations |
| GET | `/locations/{location_id}/predictions` | `hours_ahead` 1–24, default 4 |
| GET | `/users/development` | Resolves `DEV_USER_ID`; 403 when development identity is off |
| GET | `/users/{user_id}` | |
| GET | `/users/{user_id}/favorites` | Paginated |
| POST | `/users/{user_id}/favorites/{location_id}` | Idempotent |
| DELETE | `/users/{user_id}/favorites/{location_id}` | Idempotent, 204 |
| GET | `/users/{user_id}/preferences` | |
| PATCH | `/users/{user_id}/preferences` | Partial; unknown fields and explicit nulls rejected |

Filtering, search, occupancy ranges and open-status all execute in SQL — no endpoint loads the table
and filters in Python. `search` is case-insensitive across zone name, floor, building name, and
amenity name. `open_now` compares against the campus's own timezone and handles zones that close after
midnight.

### Errors

```json
{ "error": { "code": "LOCATION_NOT_FOUND", "message": "Study location was not found." } }
```

Every failure uses that envelope, and each route documents the statuses it can return. Validation
failures answer 422 without echoing the submitted values; SQLAlchemy failures answer 503 and
unexpected exceptions answer 500, both logged by exception type only. Stack traces, SQL and
credentials are never returned.

### Development identity

There is no authentication in Phase 2. `DEV_USER_ID` names a single seeded user
(`dev@studyspot.local`), and the user-scoped routes reject any other `user_id` with 403
`USER_ACCESS_DENIED`. Setting `APP_ENV=production` with `DEV_USER_ENABLED=true` fails startup, so this
shortcut cannot follow the app into production. Phase 3 replaces the path identity with an
authenticated subject; the routes and services keep their shape.

## Migrations

```sh
.venv/bin/alembic upgrade head                                  # apply
.venv/bin/alembic revision --autogenerate -m "describe change"   # author
.venv/bin/alembic check                                          # assert no model/schema drift
.venv/bin/alembic downgrade base                                 # tear down
.venv/bin/alembic current / history                              # inspect
```

The database is reproducible from migrations alone; `create_all()` is not used anywhere outside of
SQLAlchemy's own test fixtures. `alembic/env.py` reads `DATABASE_URL` through the same settings object
as the app, so a stray URL cannot slip in. Autogenerate ignores PostGIS's internal objects.

## Tests

```sh
.venv/bin/pytest -q
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

Tests require `TEST_DATABASE_URL`, refuse to run unless the database name ends in `_test`, refuse a
non-local host, and refuse a URL that matches `DATABASE_URL` — a production database cannot be
targeted by accident. The suite creates the database if needed, migrates it, seeds it once per
session, and wraps each test in a rolled-back transaction.

Covered: health; catalog listings; location list and detail; 404s; search; noise, amenity, occupancy
and open-now filters; pagination bounds; favorites including duplicates and unknown locations;
preferences including partial updates and invalid payloads; predictions and horizon windows; occupancy
classification boundaries; PostGIS extension, generated `geo_point` and index presence; database
constraints (occupancy out of range, duplicate favorite, bad foreign key); seed idempotency preserving
user edits; a bounded query count on the list endpoint (no N+1); development-identity refusal when
disabled; production refusing the demo identity; error responses hiding exception detail; and a
migration round trip.

## Deliberately not in Phase 2

Real authentication (Phase 3), proximity/radius search and walking distance (Phase 4) — the API never
invents a walking time, since no user location is supplied — crowd reports and check-in writes
(Phase 5), trained forecasting models (Phase 7), Redis, and production deployment. Every persisted
estimate, observation and prediction is `source = 'seed'` development data, not a live campus reading.
