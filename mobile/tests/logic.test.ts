import test from "node:test";
import assert from "node:assert/strict";
import {
  getOccupancyLevel,
  getOccupancyLabel,
  formatOperatingHours,
  formatWalkingDistance,
} from "../utils/occupancy";
import { filterLocations, defaultFilters } from "../utils/filters";
import { rankLocations } from "../utils/recommendations";
import { mockLocations } from "../mocks/locations";
import { defaultPreferences } from "../services/userService";

test("occupancy boundaries share the correct inclusive thresholds", () => {
  for (const [percent, level] of [
    [0, "available"],
    [39, "available"],
    [40, "moderate"],
    [64, "moderate"],
    [65, "busy"],
    [84, "busy"],
    [85, "full"],
    [100, "full"],
  ] as const)
    assert.equal(getOccupancyLevel(percent), level);
  assert.equal(getOccupancyLevel(-5), "available");
  assert.equal(getOccupancyLevel(120), "full");
  assert.equal(getOccupancyLabel(90), "Nearly full");
});
test("formatters handle midnight and walking time", () => {
  assert.equal(
    formatOperatingHours({ open: "07:00", close: "00:00" }),
    "7:00 AM – 12:00 AM",
  );
  assert.equal(
    formatOperatingHours({ open: "12:30", close: "22:00" }),
    "12:30 PM – 10:00 PM",
  );
  assert.equal(formatWalkingDistance(7), "7 min walk");
});
test("search is trimmed, case-insensitive, and includes amenities and floors", () => {
  assert.equal(
    filterLocations(mockLocations, { ...defaultFilters, query: " FENWICK " })
      .length,
    4,
  );
  assert.ok(
    filterLocations(mockLocations, {
      ...defaultFilters,
      query: "whiteboards",
    }).every((l) => l.amenities.includes("Whiteboards")),
  );
  assert.equal(
    filterLocations(mockLocations, { ...defaultFilters, query: "floor 4" })[0]
      ?.id,
    "zone-1",
  );
});
test("combined filters require every condition, and reset restores all zones", () => {
  const result = filterLocations(mockLocations, {
    ...defaultFilters,
    maxWalk: 5,
    noise: "quiet",
    crowding: "available",
    amenities: ["Whiteboards", "Group rooms"],
  });
  assert.deepEqual(
    result.map((l) => l.id),
    ["zone-6"],
  );
  assert.equal(filterLocations(mockLocations, defaultFilters).length, 12);
  assert.equal(
    filterLocations(mockLocations, { ...defaultFilters, query: "missing" })
      .length,
    0,
  );
});
test("ranking honors hard amenity and walking constraints", () => {
  const prefs = {
    ...defaultPreferences,
    maxWalk: 5,
    amenities: ["Whiteboards" as const],
  };
  const result = rankLocations(mockLocations, prefs);
  assert.equal(result.length, 1);
  assert.equal(result[0]?.location.id, "zone-6");
  assert.deepEqual(rankLocations(mockLocations, { ...prefs, maxWalk: 1 }), []);
});
test("rankings are bounded, deterministic, descending, and responsive to study style", () => {
  const quiet = rankLocations(mockLocations, {
    ...defaultPreferences,
    maxWalk: 99,
  });
  assert.ok(
    quiet.every(
      (r, i) =>
        r.score >= 0 &&
        r.score <= 100 &&
        (i === 0 || quiet[i - 1]!.score >= r.score),
    ),
  );
  assert.deepEqual(
    quiet,
    rankLocations(mockLocations, { ...defaultPreferences, maxWalk: 99 }),
  );
  const social = rankLocations(mockLocations, {
    ...defaultPreferences,
    maxWalk: 99,
    noise: "social",
    studyType: "group",
  });
  assert.notEqual(quiet[0]?.location.id, social[0]?.location.id);
});
test("study duration affects forecast and scoring", () => {
  const short = rankLocations(mockLocations, defaultPreferences).find(
    (r) => r.location.id === "zone-1",
  )!;
  const long = rankLocations(mockLocations, {
    ...defaultPreferences,
    duration: 3,
  }).find((r) => r.location.id === "zone-1")!;
  assert.ok(
    short.expectedOccupancy !== null &&
      long.expectedOccupancy !== null &&
      short.expectedOccupancy < long.expectedOccupancy,
  );
  assert.ok(short.score > long.score);
});
test("missing distance is not treated as a real walk or a ranking penalty", () => {
  const rows = mockLocations.map((l) => ({ ...l, walkingMinutes: null }));
  assert.equal(
    rankLocations(rows, { ...defaultPreferences, maxWalk: 1 }).length,
    12,
  );
});
test("missing occupancy is unknown, not an empty room", () => {
  assert.equal(getOccupancyLevel(null), "unknown");
});
