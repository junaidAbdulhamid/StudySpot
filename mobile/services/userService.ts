import { UserPreferences } from "../types";
import { apiClient, dataSchema } from "./api/client";
import { preferencesDto, userDto } from "./api/dto";
import { mapPreferencesDto, preferencesToDto } from "./api/mappers";
export const defaultPreferences: UserPreferences = {
  noise: "quiet",
  studyType: "solo",
  amenities: ["Outlets"],
  maxWalk: 10,
  duration: 1,
};
export const userService = {
  async getDevelopmentUser() {
    return (await apiClient.request("/users/development", dataSchema(userDto)))
      .data;
  },
  async getPreferences(userId: string) {
    return mapPreferencesDto(
      (
        await apiClient.request(
          `/users/${encodeURIComponent(userId)}/preferences`,
          dataSchema(preferencesDto),
        )
      ).data,
    );
  },
  async savePreferences(userId: string, preferences: UserPreferences) {
    return mapPreferencesDto(
      (
        await apiClient.request(
          `/users/${encodeURIComponent(userId)}/preferences`,
          dataSchema(preferencesDto),
          { method: "PATCH", body: preferencesToDto(preferences) },
        )
      ).data,
    );
  },
};
