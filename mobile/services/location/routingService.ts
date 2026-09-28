import { z } from "zod";
import { Coordinate } from "../../utils/geospatial";
export interface WalkingRoute {
  distanceMeters: number;
  durationSeconds: number;
  geometry: { type: "LineString"; coordinates: number[][] };
}
export interface RoutingProvider {
  getWalkingRoute(
    origin: Coordinate,
    destination: Coordinate,
  ): Promise<WalkingRoute | null>;
  clear(): void;
}
const responseSchema = z.object({
  routes: z.array(
    z.object({
      distance: z.number().nonnegative(),
      duration: z.number().nonnegative(),
      geometry: z.object({
        type: z.literal("LineString"),
        coordinates: z.array(z.array(z.number())),
      }),
    }),
  ),
});
export function createRoutingProvider(
  token: string,
  fetcher = fetch,
): RoutingProvider {
  const cache = new Map<string, { at: number; route: WalkingRoute | null }>();
  let generation = 0;
  const pending = new Set<AbortController>();
  return {
    clear() {
      generation++;
      pending.forEach((controller) => controller.abort());
      pending.clear();
      cache.clear();
    },
    async getWalkingRoute(origin, destination) {
      if (!token) return null;
      const version = generation;
      const key = `${origin.longitude},${origin.latitude};${destination.longitude},${destination.latitude}`;
      const cached = cache.get(key);
      if (cached && Date.now() - cached.at < 120000) return cached.route;
      const controller = new AbortController();
      pending.add(controller);
      const timeout = setTimeout(() => controller.abort(), 8000);
      let route: WalkingRoute | null = null;
      try {
        const response = await fetcher(
          `https://api.mapbox.com/directions/v5/mapbox/walking/${key}?geometries=geojson&overview=simplified&access_token=${encodeURIComponent(token)}`,
          { signal: controller.signal },
        );
        if (response.ok) {
          const result = responseSchema.safeParse(await response.json());
          const first = result.success ? result.data.routes[0] : null;
          if (first)
            route = {
              distanceMeters: first.distance,
              durationSeconds: first.duration,
              geometry: first.geometry,
            };
        }
      } catch {
        /* Routes are optional; never manufacture walking times. */
      } finally {
        clearTimeout(timeout);
        pending.delete(controller);
      }
      if (version !== generation) return null;
      for (const [cachedKey, value] of cache)
        if (Date.now() - value.at >= 120000) cache.delete(cachedKey);
      if (cache.size >= 10) cache.clear();
      cache.set(key, { at: Date.now(), route });
      return route;
    },
  };
}
export const routingService = createRoutingProvider(
  process.env.EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN ?? "",
);
