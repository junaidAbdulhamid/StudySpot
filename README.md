# StudySpot

A campus companion for George Mason students: find a study space by crowd level, noise, amenities, and
study style.

- **Phase 1** built the React Native + Expo mobile product — navigation, the dark forest design system,
  reusable components, and every screen.
- **Phase 2** replaced the mobile mock data layer with a real FastAPI + PostgreSQL/PostGIS backend.
  Locations, occupancy, forecasts, favorites and preferences now come from the database.
- **Phase 3** replaced the development identity with real sign-in: Supabase Auth issues the session,
  the mobile app carries it as a bearer token, and the API verifies it against Supabase on every request
  before touching `/me` or its sub-routes.

All occupancy figures and forecasts are persisted **development seed data** — not live George Mason
occupancy and not machine-learning output. Alerts remain local demo fixtures.

```text
React Native screen → mobile service → API client → HTTP
  → FastAPI router → service → repository → SQLAlchemy → PostgreSQL + PostGIS
```

## Run locally

Requires Node.js 22.13+, npm, Python 3.12+, [uv](https://docs.astral.sh/uv/), and Docker.

```sh
# 1. Database
cp -n infrastructure/.env.example infrastructure/.env         # set POSTGRES_PASSWORD
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml up -d db

# 2. API  (http://127.0.0.1:8001, docs at /docs)
cd backend
cp -n .env.example .env                                      # same password in both URLs
uv sync --python 3.12
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed.run
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# 3. Mobile  (new terminal)
cd mobile
cp -n .env.example .env                                      # set EXPO_PUBLIC_API_URL for your target
npm ci
npx expo start
```

Sign-in needs a Supabase project: create one at [supabase.com](https://supabase.com), then set
`SUPABASE_URL` / `SUPABASE_ANON_KEY` in `backend/.env` and `EXPO_PUBLIC_SUPABASE_URL` /
`EXPO_PUBLIC_SUPABASE_ANON_KEY` in `mobile/.env` from the project's Settings → API page. Add
`studyspot://auth/callback` under Authentication → URL Configuration → Redirect URLs, and enable the
Google and Apple providers if you want those buttons to work — email/password sign-in needs no extra
provider setup. Without these variables the app still starts and the login screen still renders, but
every sign-in button fails with "Sign-in needs Supabase configuration."

Start the app at onboarding, sign in or create an account, and finish the preference wizard. Logging out
clears session check-ins, reports and recent locations; favorites and preferences live in the database
under the signed-in account.

Ports 8001 and 55432 are used instead of 8000 and 5432 so StudySpot does not collide with other local
projects.

### Mobile API configuration

`EXPO_PUBLIC_API_URL` must include the `/api/v1` prefix, and Expo must be restarted after changing it.

| Target | Value |
| --- | --- |
| iOS simulator, browser preview | `http://127.0.0.1:8001/api/v1` |
| Android emulator | `http://10.0.2.2:8001/api/v1` — the emulator's alias for the host machine |
| Physical iOS/Android device | `http://<your-computer-LAN-IP>:8001/api/v1` |

For a physical device, the phone and computer must be on the same trusted network, and uvicorn must
bind somewhere the device can reach it (`--host 0.0.0.0` instead of `127.0.0.1`). Add the device origin
to `CORS_ORIGINS` only if you are testing through a browser; native requests are not subject to CORS.
Android release builds block cleartext HTTP, so plain `http://` works in development only.

If the API is unreachable, every screen shows an actionable error with a retry rather than silently
falling back to fixtures.

- **iOS device:** scan the QR code with Camera and open in compatible Expo Go.
- **Android device:** scan the QR code from compatible Expo Go.
- **iOS simulator:** install Xcode and its simulator runtime, then `npm run ios`.
- **Android emulator:** install Android Studio, configure its SDK/emulator, start the emulator, then `npm run android`.
- **Browser preview:** `npm run web`. Web is an additional validation target; the application is React Native on both mobile platforms.
- From the repository root, `npm start`, `npm run ios`, and `npm run android` forward to the mobile package after installation.

If your Expo Go app does not support SDK 57, use a matching development client (`npx expo run:ios` /
`npx expo run:android`, requiring the respective native toolchain).

## Architecture

```text
mobile/
  app/                 Expo Router routes: auth, five tabs, details, predictions,
                       reporting, recommendations, directions, saved spaces, settings
  components/          Common UI, location cards, occupancy charts, map, match scores
  theme/               Semantic colors, spacing, radii, typography
  types/               Domain contracts shared by services and UI
  services/            Location, recommendation, user, favorite and alert boundaries
  services/api/        Typed HTTP client, response DTOs, DTO → domain mappers
  services/auth/       Supabase client, secure token storage, the auth/API bridge
  store/               AuthProvider (Supabase session), AppStore (API hydration, optimistic favorites)
  hooks/               Async loading/error/retry lifecycle, location lookup, debounce
  utils/               Occupancy, search/filtering, deterministic recommendation ranking
  mocks/               Phase 1 dataset: seed source of truth and test fixture only
  assets/              Bundled illustrative study-space photos
  tests/               Logic tests, API client tests, Playwright browser journeys
backend/               FastAPI app, SQLAlchemy models, repositories, services, Alembic, seed, tests
infrastructure/        Development-only PostgreSQL + PostGIS compose file
docs/                  Database ERD and validation results
ml/                    Forecasting boundary; no model implemented
relay/                 Existing repository tooling, preserved
```

### Mobile

- Expo SDK 57, React Native 0.86, React 19.2, strict TypeScript, Expo Router.
- `StyleSheet` and centralized theme tokens drive buttons, chips, cards, headers, skeletons, avatars,
  badges, and empty/error states. No large UI framework.
- Screens call services; services call the API client; the client validates every response with zod,
  applies a 10s timeout, and maps failures to actionable messages. A malformed or unreachable API
  surfaces an error state instead of a crash or a silent fixture.
- `AuthProvider` owns the Supabase session (email/password, Google, Apple, password reset) and exposes it
  through `services/auth/bridge.ts` so the API client can attach and refresh bearer tokens without a
  circular import. Session tokens live in `expo-secure-store` (chunked past its per-item size limit),
  never in AsyncStorage. `AppStore` owns everything downstream of that session — profile, favorites,
  preferences, demo check-ins/reports and notification settings — and reloads it whenever the signed-in
  user changes. Favorites and preferences are written through the API — a favorite updates the UI
  immediately, then rolls back with a visible error if the request fails. AsyncStorage now holds only the
  device notification setting and the "seen onboarding" flag; it is no longer a data source for favorites
  or preferences. Old Phase 1 local favorites/preferences are not imported automatically; the database is
  authoritative per account.
- Occupancy classification and its thresholds are centralized and mirror the backend exactly; labels
  always accompany colors. Unknown occupancy renders as unknown, never as an empty room.
- Recommendations enforce must-have amenities as hard constraints, then score current and forecast
  occupancy, noise and study style. Ranking lives in `mobile/utils/recommendations.ts`, not in screens.
- **No walking distances are shown.** Phase 1 displayed illustrative minutes; because the backend has no
  user location, distance now reads "Distance unavailable" and contributes nothing to ranking. Real
  proximity arrives with Phase 4 geospatial search.
- The map is a deliberately schematic React Native component with selectable crowd markers and a
  preview, populated from backend location records. Positions remain schematic. It uses no map credentials or GPS; `CampusMapProps` is
  the replacement boundary for a native provider.
- Reanimated adds reduced-motion-aware onboarding fades and favorite feedback. Safe area insets, scroll
  views, wrapping and FlatLists support phone layouts down to 320px.
- Photos are bundled for offline use and are illustrative, not verified GMU photography. Sources are in
  `mobile/assets/README.md`.

### Backend

FastAPI with a strict layering — thin routers, services for orchestration, repositories for catalog and user-data
queries, Pydantic schemas for everything serialized. See [backend/README.md](backend/README.md) for the
endpoint list, environment variables, migration and test commands.

### Database

PostgreSQL 17 + PostGIS 3.5, created entirely by Alembic revision `0001`. Campus → Building → Study
location, study locations ↔ amenities, three occupancy tables (estimates, observations, predictions),
and users with preferences and favorites. Each study location carries a generated
`geography(POINT, 4326)` column with a GiST index, so Phase 4 radius search has nothing to backfill.

The ER diagram, constraints, indexes, thresholds and seed counts are in
[docs/database.md](docs/database.md).

## Validation

```sh
(cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest -q)
(cd mobile && npm run typecheck && npm run lint && npm test && npm run format:check)
(cd mobile && npm run test:e2e)  # run after backend tests; uses the same dedicated test database
(cd mobile && npx expo-doctor && npx expo export --platform all)
```

Backend tests refuse to run against anything but a local database whose name ends in `_test`, and bypass
Supabase entirely via `app.dependency_overrides` — see [backend/README.md](backend/README.md#tests).
The Playwright browser journeys (`npm run test:e2e`) predate Phase 3's real sign-in and still drive the
old development-identity endpoints and demo login button; **they need to be rewritten against a real (or
test) Supabase project before they can pass again**, since there is no way to complete Google/Apple OAuth
or read a session token from outside the app without one. This is the one piece of Phase 3 left
unverified — everything else (backend tests, typecheck, lint, format, unit tests, and all three
`expo export` bundle targets) passes as of the state described in `.handoff/JUNAID_REPORT.md`.

See [docs/VALIDATION.md](docs/VALIDATION.md) for executed checks with results, remaining device QA, and
dependency advisories. Do not run `npm audit fix --force`: the suggested fix downgrades Expo to an
incompatible SDK.

## Scope and next phases

Intentionally still mocked or absent: crowd reports and check-ins (local session state), alerts (client
fixtures), walking distance and proximity search, forecasting models, Redis, push delivery, analytics,
and production infrastructure. Account deletion has a service-layer primitive
(`AccountService.delete_application_data`) but no route yet, since deleting the local row without also
revoking the Supabase identity would let a deleted account silently recreate itself on next sign-in.

Prepared for what comes next: Phase 4 has coordinates, generated geography points and a spatial index
already in place. Phase 5 has `occupancy_observations` and the `crowd_report` source value waiting for
real submissions. Phase 7 writes into `occupancy_predictions` alongside a real `model_version`, and the
mobile prediction screen already reads whatever is persisted there.
