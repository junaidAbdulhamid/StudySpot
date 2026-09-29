# Phase 4: maps and foreground discovery

## Architecture and scope

The existing Expo Router screens, shared dark theme, API client, FastAPI service/repository layers, and Supabase account isolation remain in place. Device location is separate from the study-location catalog. No schema migration is needed: `study_locations.geo_point` already generates `geography(POINT,4326)` from longitude then latitude, with a GiST index.

`LocationProvider → locationController → deviceLocationService (expo-location)` obtains one balanced-accuracy foreground position. Home and the shared Map/Explore discovery loader send it to `locationService → /locations/nearby → LocationService → LocationRepository → PostGIS`. Detail distance uses a spherical geodesic calculation locally; small differences from PostGIS's WGS84 spheroid are expected. Raw distances are meters and route durations are seconds.

## Permission and privacy

Home explains location before the user selects **Enable Location**. **Not Now** persists only a dismissal flag; it never stores coordinates. Later prompts collapse to a small optional CTA. There is no automatic OS prompt. Denied permission, disabled services, failures, timeout and poor accuracy retain campus browsing. The OS may require Settings after denial. Indoors, location is approximate and cannot identify a floor.

The controller deduplicates simultaneous reads, reuses positions for two minutes, rejects stale/invalid positions and discards late responses after clearing. The provider clears coordinates on expiry, backgrounding and account change/unmount. There are no watches, background tasks, geofences, route histories or location analytics. Only foreground coarse/fine Android permissions are configured; iOS uses When In Use with no location background mode.

Coordinates are public nearby-query parameters and are not added to users, preferences, favorites, database records or application logs. Uvicorn access records strip query strings via `RedactQueryString`. Deployment proxies, load balancers and third-party observability must also omit query strings; application redaction cannot control upstream infrastructure. Avoid adding URL logging to the mobile client.

OpenFreeMap receives map tile requests. If configured, a walking router receives origin/destination. Provider processing and retention are outside StudySpot's database controls. Directions launched in Apple/Google Maps follow that provider's location settings. These disclosures appear in Settings.

## API and query

`GET /api/v1/locations/nearby` is public like existing location browsing. Favorites remain protected `/me` resources.

| Parameter | Contract |
| --- | --- |
| latitude | Required finite number, -90 to 90 |
| longitude | Required finite number, -180 to 180 |
| radius_meters | Default 1500, greater than zero, maximum 10000 |
| limit | Default 20, maximum 100 |
| search | Location, floor, building, amenity name |
| campus_id / building_id | Optional catalog scope |
| noise_level | quiet, moderate, social |
| amenities | Comma-separated slugs; every amenity must match |
| min_occupancy / max_occupancy | Inclusive 0–100 range |
| open_now | Uses persisted daily hours in campus timezone |

Response: `{ "data": [ { ...LocationListItem, "distance_meters": 437.2 } ] }`. It contains amenities, campus, building, current occupancy, seed predictions and history so cards do not fetch each property separately. The repository applies reusable SQL filters, `ST_DWithin(geo_point, origin, radius_meters)`, then `ST_Distance(geo_point, origin)` and orders by distance and ID. The origin is parameterized `ST_SetSRID(ST_MakePoint(longitude, latitude),4326)::geography`. Related data is loaded in a bounded number of bulk queries. No Python-wide radius scan, new GPS table, or index migration is involved.

Open-now logic handles midnight and overnight intervals; equal opening/closing means 24 hours. Hours currently describe a daily schedule, not holiday exceptions. The mobile `isLocationOpen` uses the same timezone and interval semantics.

## Maps, grouping and discovery

MapLibre was selected for native and web maps without a Mapbox account. Native `@maplibre/maplibre-react-native` uses an Expo config plugin and **requires a development build, not Expo Go**. Web uses `maplibre-gl` with its CSS. The default dark style is `https://tiles.openfreemap.org/styles/dark`; `EXPO_PUBLIC_MAP_STYLE_URL` can replace it. OpenFreeMap allows public and commercial use without a key but provides no uptime guarantee, so production operators should be ready to substitute or host tiles. See the [MapLibre Expo guide](https://maplibre.org/maplibre-react-native/docs/setup/expo/), [OpenFreeMap terms](https://openfreemap.org/tos/) and [Expo Location documentation](https://docs.expo.dev/versions/v57.0.0/sdk/location/).

`CampusMap` is a platform-specific adapter with a shared typed contract. Campus centers come from `/campuses`, never a scattered GMU constant or `(0,0)` fallback. The current position is a distinct blue marker. Recenter refreshes the short-lived position where permitted and animates the camera; without permission it retains campus browsing.

Each building has one marker, showing its least occupied matching zone with a percentage and text category as well as color. Selecting it reveals floor chips and the existing image/card/favorite/detail navigation. An accessible building selector remains usable when map tiles fail. Native/Web marker and camera behavior require device and browser QA.

Map and Explore share search, noise, amenity, occupancy, radius, open-now and nearest-sort state. Sheets hold a draft until Apply; Reset clears shared selections. Browse without coordinates is scoped to the configured campus and currently capped at 100 zones; nearby responses are capped at 100. At GMU's 12-zone/five-building scale building grouping is sufficient. Before expanding to a large campus, add server pagination/viewport search and SDK source-layer clustering; neither is implemented here. Map panning does not trigger API calls.

## Distance, walking routes and recommendations

Nearby cards explicitly label **straight-line** distance. No fixed walking minutes are produced. `RoutingProvider` accepts a configurable OSRM-compatible `/route/v1/foot` walking endpoint, validates its response and returns distance, duration and GeoJSON geometry. Only use a server configured with a pedestrian routing profile. Calls occur for selected destinations and up to three recommendation candidates, not every marker. A bounded memory cache lasts two minutes and clears with location state. Missing configuration, HTTP failures, rate limits, invalid responses and timeouts return `null`, retaining straight-line labels and external Directions.

Find Me a Spot keeps its existing simple scoring. With GPS, its walking preference selects an explicitly disclosed geographic fallback radius of 60 meters per requested minute (capped at 10 km); this is a product proximity constraint, **not a walking-time estimate or guarantee**. Without GPS that constraint is unavailable and the screen says so. Genuine route durations, when supplied to ranking, can enforce walking limits. Advanced learning remains Phase 8.

## Setup and exact manual checks

1. Configure the existing API and Supabase as described in the root README. No map account or token is needed. Optionally set `EXPO_PUBLIC_MAP_STYLE_URL` in ignored `mobile/.env` to another HTTPS MapLibre style. Optional `EXPO_PUBLIC_WALKING_ROUTE_URL` must point to an OSRM-compatible server using a pedestrian profile; do not point it at the public OSRM driving demo.
2. Dependencies are in the lockfile: run `cd mobile && npm ci`. `expo-location`, `expo-dev-client` and `@maplibre/maplibre-react-native` are already configured in `app.json`. If upgrading SDK versions, use Expo-compatible package versions.
3. Run `npx expo prebuild`, then `npx expo run:ios` (macOS/Xcode/CocoaPods) or `npx expo run:android` (Android SDK/JDK/emulator). Afterwards use `npx expo start --dev-client`. Rebuild after native/plugin changes. Native directories are generated and ignored.
4. iOS Simulator: choose **Features → Location → Custom Location**, enter latitude `38.8315`, longitude `-77.3075`, then enable location in StudySpot. Android Emulator: **Extended controls → Location → Single points**, enter the same coordinates and send/set the position. These coordinates are test inputs only; production code has no fake location override.
5. Physical device: set API URL to your computer's LAN address, bind the API to `0.0.0.0:8001`, connect on the same network and install the development build (`npx expo run:ios --device` or Android USB/device build). Grant While Using the App. Web: `npm run web`; geolocation requires localhost or HTTPS. Browser devtools Sensors can inject the test coordinates.
6. Sign in, enable location from Home, check nearby distances; Map should center near the user, display the blue position and occupancy markers, select Fenwick, choose Floor 4, open details and Directions. Confirm external Maps opens a walking route. Return, choose Nearest + Quiet + Outlets in Explore, then verify the same filters in Map. Check favorite persistence after reload.
7. Deny permission or disable OS location services: Home must not claim “near you”; campus search, filters, floors and favorites remain usable. Disconnect tiles or configure an unavailable style: an explicit error appears while the building selectors still work. Test airplane mode, an expired position, a distant position with no nearby results, and a rate-limited route response.

## Validation and remaining boundaries

See `docs/VALIDATION.md` for exact executed results. Automated tests cover SQL ordering/radius boundaries/filter combinations/coordinate validation and access-log privacy; mobile tests cover explicit permissions, denial, cache expiry, errors, late-result suppression, distance formatting, routing fallback and grouping. Playwright uses isolated test accounts and injected browser geolocation, not a production Supabase identity.

This is the Phase 4 geospatial guide. Phase 5 has since connected occupancy, reports and check-ins to the API; see [the occupancy guide](occupancy-system.md). Forecasts, imagery and alerts retain their documented demo boundaries.
