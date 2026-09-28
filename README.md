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
- **Phase 4** replaced the schematic map and fake walking minutes with real geolocation: foreground-only
  device location, a PostGIS-backed `/locations/nearby` search, an interactive Mapbox map, and honest
  distance labels that never claim a walking time StudySpot has not actually measured.

All occupancy figures and forecasts are persisted **development seed data** — not live George Mason
occupancy and not machine-learning output. Alerts remain local demo fixtures.

Phase 4 implementation details, executed checks and remaining provider/device acceptance are recorded
in [the Phase 4 report](docs/phase4-report.md).

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
`studyspot://auth/callback` under Authentication → URL Configuration → Redirect URLs, then follow
[the authentication setup guide](docs/authentication.md) for Google, bundle identifiers, and provider
callback URLs. Without these variables the app still starts and the login screen still renders, but
every sign-in button fails with "Sign-in needs Supabase configuration."

The map needs a Mapbox public token: create one at [mapbox.com](https://www.mapbox.com) (a `pk.*`
token — never a secret/download token) and set `EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN` in `mobile/.env`.
Without it, the Map tab shows a clear "map setup required" message and every other screen (including
nearby search, distances, and Directions) keeps working normally.

**`@rnmapbox/maps` is a native module and does not run in Expo Go.** Use a development build instead:

```sh
cd mobile
npx expo prebuild            # generates ios/ and android/ for the native map module
npx expo run:ios             # or: npx expo run:android
```

Use `npx expo start --dev-client` after installing the native build. Expo Go is unsupported for this
app because routes import the native map module. The web preview (`npm run web`) uses `mapbox-gl`
and needs no native build. See [docs/geospatial.md](docs/geospatial.md) for foreground permission
behavior, simulator/emulator location injection, physical-device setup, distance semantics and provider privacy.

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
  services/            Location, campus, recommendation, user, favorite and alert boundaries
  services/api/        Typed HTTP client, response DTOs, DTO → domain mappers
  services/auth/       Supabase client, secure token storage, the auth/API bridge
  services/location/   Device GPS adapter, Mapbox walking-route provider, native-maps deep link
  store/               AuthProvider (Supabase session), AppStore (API hydration, optimistic favorites),
                       LocationProvider (foreground GPS), DiscoveryProvider (shared map/list filters)
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
- `AuthProvider` owns the Supabase session (email/password, Google, password reset) and exposes it
  through `services/auth/bridge.ts` so the API client can attach and refresh bearer tokens without a
  circular import. Session tokens live in `expo-secure-store` (chunked past its per-item size limit),
  never in AsyncStorage. `AppStore` owns everything downstream of that session — profile, favorites,
  preferences, demo check-ins/reports and notification settings — and reloads it whenever the signed-in
  user changes. Favorites and preferences are written through the API — a favorite updates the UI
  immediately, then rolls back with a visible error if the request fails. AsyncStorage now holds only the
  device notification setting, location-prompt dismissal and the "seen onboarding" flag; it is no longer a data source for favorites
  or preferences. Old Phase 1 local favorites/preferences are not imported automatically; the database is
  authoritative per account.
- Occupancy classification and its thresholds are centralized and mirror the backend exactly; labels
  always accompany colors. Unknown occupancy renders as unknown, never as an empty room.
- Recommendations enforce must-have amenities as hard constraints, then score current and forecast
  occupancy, noise and study style. Ranking lives in `mobile/utils/recommendations.ts`, not in screens.
- **Distance is real, walking time is honest.** `LocationProvider` requests foreground-only permission
  (no background tracking, no location history) and holds a short-lived (2-minute) cached position.
  When it is available, Home, Explore and Map call `GET /locations/nearby`, which orders results by
  real PostGIS geodesic distance. `distanceLabel()` renders that as straight-line meters/km — it never
  invents a walking time. `directions/[id].tsx` optionally asks Mapbox's Directions API for an actual
  walking route (cached briefly, capped at 8s, silently falls back to the straight-line distance on any
  failure); only a route that Mapbox actually returned is shown as "N min walk." Without location
  permission, screens fall back to the paginated `/locations` list and disable proximity sorting rather
  than fabricate a distance.
- The Map tab is a real interactive Mapbox map (native via `@rnmapbox/maps`, web via `mapbox-gl`)
  behind a single `CampusMapProps` boundary, still using the dark forest style. Markers group by
  building, color by the shared occupancy thresholds, and open a bottom preview card that links to
  Location Details. A recenter control returns to the user's current position.
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
`geography(POINT, 4326)` column with a GiST index; `GET /locations/nearby` filters with `ST_DWithin`
and orders with `ST_Distance` against it directly — no in-Python distance filtering.

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
The Playwright journeys use the official Supabase client with a test-only GoTrue-shaped HTTP fixture.
They cover email account creation, onboarding, session restoration, persistence, logout, account
switching, and user-data isolation without production accounts. Google sign-in is configured against a
real Supabase project; see [docs/authentication.md](docs/authentication.md) for the setup.

See [docs/VALIDATION.md](docs/VALIDATION.md) for executed checks with results, remaining device QA, and
dependency advisories. Do not run `npm audit fix --force`: the suggested fix downgrades Expo to an
incompatible SDK.

## Scope and next phases

Intentionally still mocked or absent: crowd reports and check-ins (local session state), alerts (client
fixtures), forecasting models, Redis, push delivery, analytics, and production infrastructure. Walking
*routes* depend on a configured Mapbox token and fall back to straight-line distance when it is absent,
rate-limited, or fails — this is a documented fallback, not a gap. Account deletion has a service-layer
primitive (`AccountService.delete_application_data`) but no route yet, since deleting the local row
without also revoking the Supabase identity would let a deleted account silently recreate itself on next
sign-in. Marker clustering was intentionally skipped at the current ~12-location GMU scale; `mapModel.ts`
already groups markers by building, which is the first step if clustering is needed later.

Prepared for what comes next: Phase 5 has `occupancy_observations` and the `crowd_report` source value
waiting for real submissions. Phase 7 writes into `occupancy_predictions` alongside a real
`model_version`, and the mobile prediction screen already reads whatever is persisted there.
