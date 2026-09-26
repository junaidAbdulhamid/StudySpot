import { UserPreferences } from "../types";
import { rankLocations } from "../utils/recommendations";
import { locationService } from "./locationService";
export const recommendationService = {
  async getRecommendations(preferences: UserPreferences) {
    return rankLocations(await locationService.getLocations(), preferences);
  },
};
