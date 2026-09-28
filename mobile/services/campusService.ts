import { z } from "zod";
import { apiClient, pageSchema } from "./api/client";
const campus = z.object({
  id: z.string(),
  name: z.string(),
  latitude: z.number(),
  longitude: z.number(),
  timezone: z.string(),
});
export const campusService = {
  async getCampuses() {
    return (
      await apiClient.request("/campuses?page_size=100", pageSchema(campus))
    ).items;
  },
};
