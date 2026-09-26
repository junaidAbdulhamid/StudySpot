# Validation

## Phase 2 — backend and API integration

Executed September 26, 2026 on macOS with Python 3.12.14, FastAPI 0.141.1, SQLAlchemy 2.0.54,
Pydantic 2.13.5, Alembic 1.20.0, GeoAlchemy2 0.20.0, uv 0.12.9, ruff 0.16.9, PostgreSQL 17.5 with
PostGIS 3.5 (Docker), Node 26.7.0 and npm 11.19.0.

| Check | Command | Result |
| --- | --- | --- |
| Backend lint | `ruff check .` | Passed, no findings |
| Backend format | `ruff format --check .` | Passed, 44 files unchanged |
| Backend tests | `pytest -q` | Passed, 49 tests |
| Schema drift | `alembic check` | "No new upgrade operations detected" |
| Recreate from migrations | `alembic upgrade head` on an empty database | Passed; full schema built, `alembic downgrade base` also clean |
| Seed idempotency | `python -m app.seed.run` twice | Identical counts both runs: 1 campus, 5 buildings, 12 locations, 8 amenities, 12 estimates, 48 predictions, 96 observations, 1 user, 1 preference row, 2 favorites |
| PostGIS | `select postgis_version()` on the rebuilt database | `3.5`; all 12 locations have a non-null generated `geo_point` |
| API startup | `uvicorn app.main:app --port 8001` | Started, structured startup log emitted |
| API docs | `GET /docs`, `/redoc`, `/openapi.json` | 200; all 15 operations carry a summary and documented error statuses |
| Mobile typecheck | `npm run typecheck` | Passed, strict TypeScript |
| Mobile lint | `npm run lint` | Passed |
| Mobile format | `npm run format:check` | Passed |
| Mobile tests | `npm test` | Passed, 16 logic and API-client tests |
| Browser journeys | `npm run test:e2e` | Passed, 3 journeys in Chrome (27.3s) against a seeded `_test` database |
| Dependency check | `npx expo install --check` | Dependencies up to date |
| Expo Doctor | `npx expo-doctor` | 21/21 checks passed |
| Bundles | `npx expo export --platform all` | Passed; iOS 4.3MB and Android 4.4MB Hermes bundles, 2.6MB web bundle |

### Manual API verification

Against the development database on `http://127.0.0.1:8001/api/v1`:

| Request | Result |
| --- | --- |
| `GET /health` | 200 `{"status":"ok","database":"connected","postgis":"enabled"}` |
| `GET /campuses` | 200, 1 item (GMU Fairfax, `America/New_York`) |
| `GET /buildings` | 200, 5 items |
| `GET /locations?page_size=2` | 200, paginated envelope, `total` 12 |
| `GET /locations?search=fenwick` | 200, 4 Fenwick zones |
| `GET /locations?noise_level=quiet` | 200, quiet zones only |
| `GET /locations?amenities=outlets,whiteboards` | 200, zones carrying both |
| `GET /locations?max_occupancy=50` | 200, filtered in SQL |
| `GET /locations?page_size=500` | 422 `{"error":{"code":"VALIDATION_ERROR",...}}` |
| `GET /locations/zone-4` | 200 with building, campus, amenities, hours, current occupancy, forecasts, observations |
| `GET /locations/does-not-exist` | 404 `LOCATION_NOT_FOUND` |
| `GET /locations/zone-4/predictions?hours_ahead=4` | 200, 4 records, each `source: "seed"`, `model_version: "seed-v1"` |
| `GET /users/development` | 200, `dev@studyspot.local` |
| `GET /users/dev-studyspot/favorites` | 200, paginated |
| `POST .../favorites/zone-3` twice | 200 both times, same favorite id — no duplicate |
| `DELETE .../favorites/zone-3` | 204 |
| `GET /users/dev-studyspot/preferences` | 200 |
| `PATCH /users/dev-studyspot/preferences` | 200, partial update applied, untouched fields preserved |

### Mobile ↔ API verification

The Expo web client was run against the real development database (not the test database) with
`EXPO_PUBLIC_API_URL=http://127.0.0.1:8001/api/v1`, following the documented developer flow start to
finish: container → migrations → seed → uvicorn → `expo start --web` → onboarding.

- Home renders the greeting, campus line ("GEORGE MASON · FAIRFAX CAMPUS") and "Best spots for you"
  from API records.
- Explore reports "12 study spaces · Seed data", and typing "Fenwick" narrows it to 4 through a
  debounced database query, not a client-side filter over a prefetched list.
- Location cards show occupancy percent with its label ("72% · Busy", "53% · Moderate"), noise,
  amenities, occupancy bar, and favorite control.
- Location detail renders hours, description, amenities and occupancy from the detail endpoint.
- The predictions screen charts persisted forecasts (28% now, then 39/61/79/67%) with the insight card
  computed from those records, plus the "Recent observations" history.
- Every screen shows "Distance unavailable" — no walking time is displayed or scored anywhere.
- No page errors were raised during the journey.

Screenshots were inspected at 390 × 844; the Phase 1 dark forest design is unchanged.

The three Playwright journeys (onboarding, search/filtering, predictions, check-in and check-out,
reporting, recommendations, favorites, map selection, alerts, preference editing, settings, and a
320px viewport) run against port 8002 backed by the `_test` database, so they never disturb
development favorites or preferences.

### Phase 2 limitations

- **Seed forecasts expire.** Predictions are written for the next four hour boundaries at seed time,
  so after roughly four hours `GET /locations/{id}/predictions` returns an empty list. The predictions
  screen states this explicitly rather than inventing values; re-running `python -m app.seed.run`
  refreshes them. Real forecasting is Phase 7.
- **One identity.** `DEV_USER_ID` names a single seeded development user. Every user-scoped route
  rejects other ids with 403, and enabling it under `APP_ENV=production` fails startup. This is not
  authentication.
- **No distance.** The backend receives no user location and therefore computes no walking time. The
  Phase 1 distance display and the Explore distance filter were removed rather than left showing
  fabricated minutes.
- **Check-ins, crowd reports and alerts remain local/demo.** Phase 2 persists the tables that Phase 5
  will write into, but adds no write path for them.
- **Native device execution is still unverified.** This machine has no Xcode simulator runtime or
  Android SDK/emulator; iOS and Android bundles compile but were not launched on a device.
- **Emulated database image.** `postgis/postgis:17-3.5` has no arm64 build and runs under emulation on
  Apple Silicon. Behavior is correct; startup is a few seconds slower.
- The npm advisories recorded under Phase 1 are unchanged.

## Phase 1 — mobile application

Executed September 25–26, 2026 with Node 26.7.0, npm 11.19.0, Expo 57.0.25, React Native 0.86.3, and
React 19.2.3 on macOS.

| Check | Result |
| --- | --- |
| Dependency installation | Completed; lockfile created under `mobile/` |
| `npm run typecheck` | Passed, strict TypeScript, no errors |
| `npm run lint` | Passed, no errors or warnings |
| `npm test` | Passed, 8 logic tests |
| `npx expo install --check` | Dependencies up to date |
| `npx expo-doctor` | 21/21 checks passed |
| `npx expo export --platform all` | Passed, fresh iOS and Android Hermes bundles and web bundle |
| `npm run test:e2e` | Passed, 3 browser journeys in Chrome |
| `git diff --check` | Passed |

The initial Expo installer hit an npm 11 `--allow-scripts` compatibility error after writing
SDK-compatible dependency versions. A direct `npm install` completed installation. React type
definitions were aligned to Expo's supported version; the final compatibility checks pass.

### Exercised behavior

1. Three onboarding slides → demo Mason continuation → all four preference steps → Home → Explore
   search → Fenwick Floor 4 details → forecast/live tabs → check-in → crowd selection/submission →
   Home → Find Me a Spot and duration selection → ranked results → location favorite → directions →
   schematic map marker preview → alerts and empty state → Profile → favorites → notification setting
   → logout. No browser runtime errors were observed in this journey.
2. At a 320 × 700 viewport: distance filter, matching result counts, search empty state, filter reset,
   favorite removal, reload, repeat login, and persisted favorite state. No document horizontal
   overflow on the detail screen.
3. Home search submission, Peterson details, check-in/check-out, recent history, preference editor
   (noise, group, amenity, walking distance), appearance/privacy/about screens, and no-match
   recommendations.

Home and map screenshots were visually inspected at 390 × 844. Generated screenshots/traces live in
ignored `mobile/test-results/`; they can be regenerated with the browser tests.

Logic tests cover every occupancy threshold boundary, operating-hours formatting including midnight,
combined search/filters, hard recommendation constraints, deterministic bounded scores, changing study
styles/durations, and known/unknown location-service IDs. Phase 2 added API-client coverage for
validation, timeouts, pagination, DTO mapping and preference round trips.

### Remaining native QA

This machine has no installed Xcode simulator runtime or Android SDK/emulator. iOS and Android bundles
compile, but neither platform was launched on a simulator or physical phone. Before release, run the
README device instructions and check native gestures/back navigation, text scaling, VoiceOver/TalkBack,
safe area insets, keyboard handling, reduced motion, and persistent storage on both platforms.
Additionally verify API reachability from a physical device on the LAN. Browser testing cannot certify
these native behaviors.

### Dependency advisories

`npm audit` reports 13 moderate findings in the transitive dependency graph, stemming from `uuid`
through Expo's Xcode tooling and `decode-uri-component` through Expo Router's query-string dependency.
No high/critical findings were reported. npm's suggested force fixes downgrade Expo to SDK 46 and
Router to version 5, which is incompatible with this project; no force downgrade or unverified
dependency override was applied. Recheck upstream compatible patches before public release.

### Scope limits

Photos illustrate study spaces and are not verified GMU photography. The schematic map and directions
are previews with no GPS or routing provider. Phase 1's local mock data layer has been replaced by the
Phase 2 API; `mobile/mocks/locations.ts` survives only as the seed's source of truth and a test
fixture.
