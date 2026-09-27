import test from "node:test";
import assert from "node:assert/strict";
import { z } from "zod";
import {
  createApiClient,
  ApiError,
  collectPages,
} from "../services/api/client";
import { locationDto } from "../services/api/dto";
import {
  mapLocationDtoToStudyLocation,
  mapPreferencesDto,
  preferencesToDto,
} from "../services/api/mappers";
import { defaultPreferences } from "../services/userService";
import { AuthBridge } from "../services/auth/bridge";
const transport =
  (body: unknown, status = 200): typeof fetch =>
  async () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
test("API client validates valid responses and handles 204", async () => {
  assert.deepEqual(
    await createApiClient("http://test", 100, transport({ ok: true })).request(
      "/health",
      z.object({ ok: z.boolean() }),
    ),
    { ok: true },
  );
  assert.equal(
    await createApiClient(
      "http://test",
      100,
      async () => new Response(null, { status: 204 }),
    ).request("/favorite", z.undefined(), { method: "DELETE" }),
    undefined,
  );
});
test("API errors preserve safe server codes and network failure is actionable", async () => {
  await assert.rejects(
    createApiClient(
      "http://test",
      100,
      transport(
        {
          error: {
            code: "LOCATION_NOT_FOUND",
            message: "Study location was not found.",
          },
        },
        404,
      ),
    ).request("/missing", z.unknown()),
    (e: unknown) =>
      e instanceof ApiError &&
      e.code === "LOCATION_NOT_FOUND" &&
      e.status === 404,
  );
  await assert.rejects(
    createApiClient("http://test", 100, async () => {
      throw new TypeError("offline");
    }).request("/locations", z.unknown()),
    (e: unknown) => e instanceof ApiError && e.code === "NETWORK",
  );
});
test("timeouts abort in-flight fetches", async () => {
  const never: typeof fetch = (_input, init) =>
    new Promise((_resolve, reject) =>
      init?.signal?.addEventListener("abort", () =>
        reject(new Error("aborted")),
      ),
    );
  await assert.rejects(
    createApiClient("http://test", 5, never).request("/locations", z.unknown()),
    (e: unknown) => e instanceof ApiError && e.code === "TIMEOUT",
  );
});
test("invalid response shapes and missing configuration are errors", async () => {
  await assert.rejects(
    createApiClient("http://test", 100, transport({ items: "bad" })).request(
      "/locations",
      z.object({ items: z.array(z.string()) }),
    ),
    (e: unknown) => e instanceof ApiError && e.code === "INVALID_RESPONSE",
  );
  await assert.rejects(
    createApiClient(undefined).request("/locations", z.unknown()),
    (e: unknown) => e instanceof ApiError && e.code === "CONFIGURATION",
  );
});
test("paginated service consumers read every page", async () => {
  const pages: number[] = [];
  const items = await collectPages(async (page) => {
    pages.push(page);
    return { items: page === 1 ? [1, 2] : [3], page, page_size: 2, total: 3 };
  });
  assert.deepEqual(items, [1, 2, 3]);
  assert.deepEqual(pages, [1, 2]);
});

test("protected requests attach a bearer token", async () => {
  let authorization: string | null = null;
  const auth: AuthBridge = {
    subject: () => "user-a",
    token: async () => "access-a",
    refresh: async () => null,
    invalidate: async () => {},
  };
  const client = createApiClient(
    "http://test",
    100,
    async (_input, init) => {
      authorization = new Headers(init?.headers).get("Authorization");
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    },
    () => auth,
  );
  await client.request("/me", z.object({ ok: z.boolean() }));
  assert.equal(authorization, "Bearer access-a");
});

test("a 401 refreshes once and retries with the new token", async () => {
  const tokens: (string | null)[] = [];
  let calls = 0;
  let refreshes = 0;
  const auth: AuthBridge = {
    subject: () => "user-a",
    token: async () => "expired",
    refresh: async () => {
      refreshes++;
      return "fresh";
    },
    invalidate: async () => assert.fail("valid refresh must not sign out"),
  };
  const client = createApiClient(
    "http://test",
    100,
    async (_input, init) => {
      calls++;
      tokens.push(new Headers(init?.headers).get("Authorization"));
      return new Response(JSON.stringify(calls === 1 ? {} : { ok: true }), {
        status: calls === 1 ? 401 : 200,
      });
    },
    () => auth,
  );
  assert.deepEqual(
    await client.request("/me/preferences", z.object({ ok: z.boolean() })),
    { ok: true },
  );
  assert.equal(refreshes, 1);
  assert.equal(calls, 2);
  assert.deepEqual(tokens, ["Bearer expired", "Bearer fresh"]);
});

test("an invalid refresh signs out once and never loops", async () => {
  let calls = 0;
  let invalidations = 0;
  const auth: AuthBridge = {
    subject: () => "user-a",
    token: async () => "expired",
    refresh: async () => null,
    invalidate: async () => {
      invalidations++;
    },
  };
  await assert.rejects(
    createApiClient(
      "http://test",
      100,
      async () => {
        calls++;
        return new Response(JSON.stringify({}), { status: 401 });
      },
      () => auth,
    ).request("/me", z.unknown()),
    (error: unknown) =>
      error instanceof ApiError && error.code === "UNAUTHORIZED",
  );
  assert.equal(calls, 1);
  assert.equal(invalidations, 1);
});

test("account switching cancels an in-flight protected response", async () => {
  let subject = "user-a";
  const auth: AuthBridge = {
    subject: () => subject,
    token: async () => {
      subject = "user-b";
      return "token-a";
    },
    refresh: async () => null,
    invalidate: async () => {},
  };
  let sent = false;
  await assert.rejects(
    createApiClient(
      "http://test",
      100,
      async () => {
        sent = true;
        return new Response(JSON.stringify({}));
      },
      () => auth,
    ).request("/me", z.unknown()),
    (error: unknown) =>
      error instanceof ApiError && error.code === "SESSION_CHANGED",
  );
  assert.equal(sent, false);
});
test("DTO mapping preserves missing data and never fabricates distance", () => {
  const dto = locationDto.parse({
    id: "zone-1",
    name: "Fenwick Library",
    floor: "Floor 4",
    description: "A quiet space",
    capacity: 40,
    latitude: 38.83,
    longitude: -77.3,
    building: { id: "fenwick", name: "Fenwick Library", campus_id: "gmu" },
    campus: {
      id: "gmu",
      name: "Fairfax",
      university_name: "GMU",
      timezone: "America/New_York",
    },
    amenities: [
      { id: "outlets", name: "Outlets", slug: "outlets", icon: "flash" },
    ],
    noise_level: "quiet",
    image_url: null,
    hours: { open: "07:00", close: "00:00" },
    current_occupancy: null,
    predictions: [],
    historical: [],
  });
  const location = mapLocationDtoToStudyLocation(dto);
  assert.equal(location.walkingMinutes, null);
  assert.equal(location.currentOccupancy, null);
  assert.deepEqual(location.predictions, []);
  assert.deepEqual(location.amenities, ["Outlets"]);
  assert.equal(locationDto.safeParse({ ...dto, latitude: 100 }).success, false);
});
test("preferences round-trip from UI through API naming without losing fields", () => {
  const value = {
    ...defaultPreferences,
    studyType: "either" as const,
    duration: 3,
  };
  const dto = preferencesToDto(value);
  const mapped = mapPreferencesDto({
    id: "p",
    user_id: "dev",
    ...dto,
    preferred_amenities: [
      { id: "outlets", name: "Outlets", slug: "outlets", icon: "flash" },
    ],
  });
  assert.deepEqual(mapped, value);
});
