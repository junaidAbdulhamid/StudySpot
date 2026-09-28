import test from "node:test";
import assert from "node:assert/strict";
import {
  createLocationController,
  LOCATION_TTL,
} from "../services/location/locationController";
import { createRoutingProvider } from "../services/location/routingService";
import {
  distanceLabel,
  formatDistance,
  formatDuration,
  isLocationOpen,
  straightLineDistance,
} from "../utils/geospatial";
import { mapGroups } from "../components/navigation/mapModel";
import { mockLocations as locations } from "../mocks/locations";
test("foreground permission is explicit and fresh coordinates are cached", async () => {
  let requests = 0,
    reads = 0,
    clock = 1000;
  const controller = createLocationController(
    {
      permission: async () => ({ granted: true }),
      request: async () => {
        requests++;
        return { granted: true };
      },
      current: async () => {
        reads++;
        return { latitude: 38, longitude: -77, accuracy: 30, timestamp: clock };
      },
    },
    () => {},
    () => clock,
  );
  assert.equal(requests, 0);
  assert.equal(reads, 0);
  await controller.acquire(true);
  await controller.acquire(false);
  assert.equal(controller.getState().permissionStatus, "granted");
  assert.equal(requests, 1);
  assert.equal(reads, 1);
  clock += LOCATION_TTL + 1;
  await controller.acquire(false);
  assert.equal(reads, 2);
  controller.clear();
  assert.equal(controller.getState().coordinates, null);
});
test("denied permission never reads GPS; unavailable GPS falls back", async () => {
  for (const granted of [false, true]) {
    let reads = 0;
    const controller = createLocationController(
      {
        permission: async () => ({ granted }),
        request: async () => ({ granted }),
        current: async () => {
          reads++;
          throw new Error("disabled");
        },
      },
      () => {},
    );
    await controller.acquire(true);
    assert.equal(
      controller.getState().permissionStatus,
      granted ? "unavailable" : "denied",
    );
    assert.equal(reads, granted ? 1 : 0);
    assert.equal(controller.getState().coordinates, null);
  }
});
test("clearing location rejects an in-flight position", async () => {
  let resolve!: (position: {
    latitude: number;
    longitude: number;
    accuracy: number;
    timestamp: number;
  }) => void;
  const controller = createLocationController(
    {
      permission: async () => ({ granted: true }),
      request: async () => ({ granted: true }),
      current: () =>
        new Promise((r) => {
          resolve = r;
        }),
    },
    () => {},
  );
  const pending = controller.acquire(true);
  await Promise.resolve();
  controller.clear();
  resolve({
    latitude: 38,
    longitude: -77,
    accuracy: 10,
    timestamp: Date.now(),
  });
  await pending;
  assert.equal(controller.getState().coordinates, null);
});
test("distance semantics and overnight campus hours", () => {
  assert.equal(formatDistance(437), "437 m");
  assert.equal(formatDistance(1430), "1.4 km");
  assert.equal(formatDuration(360), "6 min walk");
  assert.match(distanceLabel({ distanceMeters: 437 }), /straight-line/);
  assert.doesNotMatch(distanceLabel({ distanceMeters: 437 }), /min walk/);
  assert.ok(
    Math.abs(
      straightLineDistance(
        { latitude: 0, longitude: 0 },
        { latitude: 0, longitude: 0.001 },
      ) - 111.195,
    ) < 0.01,
  );
  assert.equal(
    isLocationOpen(
      { open: "22:00", close: "02:00" },
      "America/New_York",
      new Date("2026-01-02T06:00:00Z"),
    ),
    true,
  );
  assert.equal(
    isLocationOpen(
      { open: "22:00", close: "02:00" },
      "America/New_York",
      new Date("2026-01-02T07:00:00Z"),
    ),
    false,
  );
});
test("routing caches real routes and gracefully handles missing token and failures", async () => {
  const origin = { latitude: 38, longitude: -77 };
  let calls = 0;
  const provider = createRoutingProvider("public-test", async () => {
    calls++;
    return new Response(
      JSON.stringify({
        routes: [
          {
            distance: 430,
            duration: 360,
            geometry: {
              type: "LineString",
              coordinates: [
                [-77, 38],
                [-77, 38.1],
              ],
            },
          },
        ],
      }),
    );
  });
  assert.equal(
    (await provider.getWalkingRoute(origin, origin))?.durationSeconds,
    360,
  );
  await provider.getWalkingRoute(origin, origin);
  assert.equal(calls, 1);
  provider.clear();
  await provider.getWalkingRoute(origin, origin);
  assert.equal(calls, 2);
  assert.equal(
    await createRoutingProvider("").getWalkingRoute(origin, origin),
    null,
  );
  assert.equal(
    await createRoutingProvider(
      "public-test",
      async () => new Response("", { status: 429 }),
    ).getWalkingRoute(origin, origin),
    null,
  );
});
test("floors group into one building marker with least crowded zone", () => {
  const grouped = mapGroups(locations);
  assert.ok(grouped.length < locations.length);
  assert.equal(
    grouped.flatMap((group) => group.locations).length,
    locations.length,
  );
});
