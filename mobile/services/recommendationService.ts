import { UserPreferences } from "../types";
import { rankLocations } from "../utils/recommendations";
import { locationService } from "./locationService";
import { Coordinate } from "../utils/geospatial";
import { routingService } from "./location/routingService";
export const recommendationService = {
  async getRecommendations(
    preferences: UserPreferences,
    coordinates?: Coordinate | null,
  ) {
    const locations = coordinates
      ? await locationService.getNearbyLocations(
          coordinates.latitude,
          coordinates.longitude,
          { radiusMeters: Math.min(10000, preferences.maxWalk * 60) },
        )
      : await locationService.getLocations();
    const ranked = rankLocations(locations, preferences);
    if (!coordinates) return ranked;
    const routed = await Promise.all(
      ranked.slice(0, 3).map(async (match) => {
        const route = await routingService.getWalkingRoute(
          coordinates,
          match.location,
        );
        return route
          ? { ...match.location, walkingDurationSeconds: route.durationSeconds }
          : match.location;
      }),
    );
    return rankLocations(
      [...routed, ...ranked.slice(3).map((match) => match.location)],
      preferences,
    );
  },
};
