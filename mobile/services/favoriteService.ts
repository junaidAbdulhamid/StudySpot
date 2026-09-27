import { z } from "zod";
import { apiClient, collectPages, dataSchema, pageSchema } from "./api/client";
import { favoriteDto } from "./api/dto";
export const favoriteService = {
  async getFavorites() {
    const rows = await collectPages((page) =>
      apiClient.request(
        `/me/favorites?page=${page}&page_size=100`,
        pageSchema(favoriteDto),
      ),
    );
    return rows.map((row) => row.location_id);
  },
  async add(locationId: string) {
    await apiClient.request(
      `/me/favorites/${encodeURIComponent(locationId)}`,
      dataSchema(favoriteDto),
      { method: "POST" },
    );
  },
  async remove(locationId: string) {
    await apiClient.request(
      `/me/favorites/${encodeURIComponent(locationId)}`,
      z.undefined(),
      { method: "DELETE" },
    );
  },
};
