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
  async updateProfile(display_name: string) {
    return (
      await apiClient.request("/me", dataSchema(userDto), {
        method: "PATCH",
        body: { display_name },
      })
    ).data;
  },
  async getMe() {
    return (await apiClient.request("/me", dataSchema(userDto))).data;
  },
  async getPreferences() {
    return mapPreferencesDto(
      (await apiClient.request("/me/preferences", dataSchema(preferencesDto)))
        .data,
    );
  },
  async savePreferences(preferences: UserPreferences) {
    return mapPreferencesDto(
      (
        await apiClient.request("/me/preferences", dataSchema(preferencesDto), {
          method: "PATCH",
          body: preferencesToDto(preferences),
        })
      ).data,
    );
  },
};
