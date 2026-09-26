# Development infrastructure

`compose.yaml` runs one service — PostgreSQL 17 with PostGIS 3.5 — so local development has a
reproducible database. This is development tooling only. Production containerization, orchestration,
and cloud infrastructure are a later phase; nothing here is intended to be deployed.

## Start the database

```sh
cp infrastructure/.env.example infrastructure/.env   # then set POSTGRES_PASSWORD
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml up -d db
```

Then follow [../backend/README.md](../backend/README.md) for migrations, seeding and the API.

```sh
# status, logs, stop
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml ps
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml logs -f db
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml down          # keeps data
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml down -v       # deletes data
```

After `down -v`, re-run `alembic upgrade head` and the seed command to rebuild the database from
migrations.

## Configuration

`infrastructure/.env` is not committed. `POSTGRES_PASSWORD` has no default and compose refuses to start
without it; use the same value in `backend/.env`.

| Variable | Default | Notes |
| --- | --- | --- |
| `POSTGRES_USER` | `studyspot` | |
| `POSTGRES_PASSWORD` | — | Required. Local development credential only |
| `POSTGRES_DB` | `studyspot` | Tests use a second database whose name ends in `_test` |
| `POSTGRES_PORT` | `55432` | Host port |

Notes on the choices:

- **Port 55432, not 5432.** The container publishes on a non-default host port so StudySpot does not
  collide with another PostgreSQL already running locally. The API's port 8001 is chosen the same way.
- **Bound to `127.0.0.1`.** The port mapping is loopback-only, so the database is not reachable from
  the local network. Mobile devices talk to the API, never to PostgreSQL.
- **`platform: linux/amd64`.** The PostGIS image has no arm64 build, so it runs through emulation on
  Apple Silicon. Startup takes a few seconds longer; queries at this data size are unaffected.
- **Named volume `studyspot_data`.** Data survives `down` but not `down -v`. Since everything is
  reproducible from `alembic upgrade head` plus the seed, deleting the volume is always safe.
- **Healthcheck.** `pg_isready` gates the container as healthy, which is what the test harness and
  compose dependents wait on.
