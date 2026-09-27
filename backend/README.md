# StudySpot API

FastAPI + SQLAlchemy 2 + PostgreSQL/PostGIS. Phase 2 built the persistent campus data foundation the
mobile app reads from; Phase 3 replaced the development identity with real sign-in verified against
Supabase Auth. Live occupancy, crowd reporting, proximity search, and forecasting models are later
phases and are not implemented here.

## Layering

```text
FastAPI router (app/api/v1/*)      HTTP parameters, status codes, response models
  → service     (app/services/*)   orchestration, not-found policy, assembly
    → repository (app/repositories/*) queries, filters, persistence
      → SQLAlchemy models (app/models/entities.py)
        → PostgreSQL + PostGIS
```

Route handlers stay thin — they resolve dependencies and hand off. Business rules live in services;
catalog and user-data queries live in repositories. Pydantic schemas (`app/schemas/catalog.py`) are the only thing
serialized; ORM instances never leave the service layer.

| Path | Contents |
| --- | --- |
| `app/main.py` | App factory, CORS, exception handlers, lifespan/logging, `/docs` and `/redoc` |
| `app/core/config.py` | `pydantic-settings` config, `.env`, validation of unsafe combinations |
| `app/core/database.py` | One cached engine with `pool_pre_ping`, session factory, `get_db` dependency |
| `app/core/exceptions.py` | `AppError` plus handlers that map everything to one error envelope |
| `app/core/logging.py` | JSON log formatter on the `studyspot` logger |
| `app/api/dependencies.py` | `Database` session dependency and the `CurrentUser` auth dependency chain |
| `app/core/auth.py` | Verifies bearer tokens against Supabase Auth's `/auth/v1/user`; trusts no local JWT parsing |
| `app/services/accounts.py` | `AccountService` — synchronizes a verified identity to a local `User` row |
| `app/models/` | Declarative base with a naming convention, enums, all entities |
| `app/repositories/` | `Campus`, `Building`, `Location`, `Occupancy`, `Prediction`, `User`, `Favorite`, `Preference` |
| `app/services/` | `CampusService`, `BuildingService`, `LocationService`, `PredictionService`, `AccountService`, `FavoriteService`, `PreferenceService` |
| `app/utils/occupancy.py` | `classify_occupancy()` — the single threshold definition |
| `app/seed/` | Idempotent development seed plus `phase1.json` exported from the Phase 1 dataset |
| `alembic/` | Migrations; `0001` is the Phase 2 schema, `0002` adds Supabase-linked accounts |
| `tests/` | 68 pytest tests against a dedicated `_test` database |

Schema details, the ER diagram, constraints, indexes and seed counts are in
[../docs/database.md](../docs/database.md).

## Local setup

Requires Python 3.12+ and Docker (for PostGIS). [uv](https://docs.astral.sh/uv/) manages the
environment; `uv.lock` is committed.

```sh
# 1. Start PostgreSQL + PostGIS (from repository root)
cp -n infrastructure/.env.example infrastructure/.env     # then set POSTGRES_PASSWORD
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml up -d db

# 2. Configure and install
cd backend
cp -n .env.example .env                                   # same password in both URLs
uv sync --python 3.12

# 3. Create the schema and load development data
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed.run

# 4. Run
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

`http://127.0.0.1:8001/docs` and `/redoc` are served in development and test, and are disabled when
`APP_ENV=production`. Port 8001 (and database port 55432) were chosen to avoid colliding with other
local projects on 8000/5432; change the database port in compose configuration and the API port in the uvicorn command if needed.

Re-run `.venv/bin/python -m app.seed.run` whenever the demo forecasts have gone stale — seeded
predictions only cover four hours from the moment they were written.

## Environment variables

`backend/.env`, never committed. See `.env.example`. Existing shell variables take precedence over `.env`; if another tool sets `DEBUG=release`, unset it or run these commands with `DEBUG=false`.

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_ENV` | `development` | `development` \| `test` \| `production` |
| `DEBUG` | `false` | Must be `false` when `APP_ENV=production` |
| `DATABASE_URL` | — | Required; must use the `postgresql+psycopg://` driver |
| `API_V1_PREFIX` | `/api/v1` | Leading slash, no trailing slash |
| `CORS_ORIGINS` | `[]` | JSON list of explicit origins; `*` is rejected |
| `SUPABASE_URL` | `""` | Your Supabase project's HTTPS URL; blank disables `/me` and its sub-routes |
| `SUPABASE_ANON_KEY` | `""` | The project's anon/public key, sent as `apikey` when verifying tokens |
| `DEV_USER_ENABLED` | `false` | Gates `app.seed.run` only; must be `false` when `APP_ENV=production` |
| `DEV_USER_ID` | `dev-studyspot` | The id the seed script assigns to its demo user |
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
| GET | `/me` | The signed-in account; created on first sign-in |
| PATCH | `/me` | Partial profile update (`display_name`, `avatar_url`) |
| GET | `/me/favorites` | Paginated |
| POST | `/me/favorites/{location_id}` | Idempotent |
| DELETE | `/me/favorites/{location_id}` | Idempotent, 204 |
| GET | `/me/preferences` | |
| PATCH | `/me/preferences` | Partial; unknown fields and explicit nulls rejected |

All `/me` routes require `Authorization: Bearer <supabase-access-token>` and answer 401
`UNAUTHORIZED` without one, or 503 `AUTH_UNAVAILABLE` if `SUPABASE_URL`/`SUPABASE_ANON_KEY` are unset
or Supabase itself is unreachable.

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

### Authentication

`/me` and its sub-routes trust nothing about a JWT locally: `app/core/auth.py` sends the bearer token
to the configured Supabase project's `/auth/v1/user` endpoint and only accepts a 200 response. On each
authenticated request, `AccountService.synchronize` (`app/services/accounts.py`) upserts a local `User`
row keyed on the verified `auth_provider_id`, refreshing `email` but never overwriting `display_name` —
so an in-app profile edit survives the next sign-in. A first sign-in also creates default preferences.

Migration `0002` replaced the old `uq_users_email` constraint with a unique, nullable
`auth_provider_id`, since email is no longer how an account is found or merged. `DEV_USER_ID` is now
only used by `app.seed.run` to label the demo user seeded for local development and tests; it is
unrelated to signing in and grants no route access. Setting `APP_ENV=production` with
`DEV_USER_ENABLED=true` still fails startup.

## Migrations

```sh
.venv/bin/alembic upgrade head                                  # apply
.venv/bin/alembic revision --autogenerate -m "describe change"   # author
.venv/bin/alembic check                                          # assert no model/schema drift
.venv/bin/alembic downgrade base                                 # tear down
.venv/bin/alembic current
.venv/bin/alembic history                              # inspect
```

The database is reproducible from migrations alone; `create_all()` is not used by the application or tests. `alembic/env.py` reads `DATABASE_URL` through the same settings object
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
and open-now filters; pagination bounds; `/me` profile read/update; favorites including duplicates and
unknown locations; preferences including partial updates and invalid payloads; predictions and horizon
windows; occupancy classification boundaries; PostGIS extension, generated `geo_point` and index
presence; database constraints (occupancy out of range, duplicate favorite, bad foreign key); seed
idempotency preserving user edits; a bounded query count on the list endpoint (no N+1); token
verification (missing/malformed/expired bearer, Supabase unconfigured or unreachable, anonymous or
malformed identities); account synchronization (creation, email refresh without overwriting
`display_name`, idempotent preference creation, cascading deletion); production refusing the demo seed
identity; error responses hiding exception detail; and a migration round trip.

The `client` fixture bypasses `app/core/auth.py` entirely via `app.dependency_overrides`, authenticating
every request as the seeded dev user — this is the standard FastAPI pattern for testing routes that sit
behind a real third-party identity provider. `test_auth.py` covers `verify_access_token` and
`AccountService` directly, and `anonymous_client` (no override) covers the real 401/503 route behavior.

## Deliberately not implemented

Proximity/radius search and walking distance (Phase 4) — the API never invents a walking time, since no
user location is supplied — crowd reports and check-in writes (Phase 5), trained forecasting models
(Phase 7), Redis, and production deployment. Every persisted estimate, observation and prediction is
`source = 'seed'` development data, not a live campus reading. Account deletion has no route yet;
`AccountService.delete_application_data` exists as the internal primitive a future endpoint will call
once it also revokes the Supabase identity.
