import { z } from "zod";
import { apiClient, collectPages, dataSchema, pageSchema } from "./api/client";
import { favoriteDto } from "./api/dto";
export const favoriteService = {
  async getFavorites(userId: string) {
    const rows = await collectPages((page) =>
      apiClient.request(
        `/users/${encodeURIComponent(userId)}/favorites?page=${page}&page_size=100`,
        pageSchema(favoriteDto),
      ),
    );
    return rows.map((row) => row.location_id);
  },
  async add(userId: string, locationId: string) {
    await apiClient.request(
      `/users/${encodeURIComponent(userId)}/favorites/${encodeURIComponent(locationId)}`,
      dataSchema(favoriteDto),
      { method: "POST" },
    );
  },
  async remove(userId: string, locationId: string) {
    await apiClient.request(
      `/users/${encodeURIComponent(userId)}/favorites/${encodeURIComponent(locationId)}`,
      z.undefined(),
      { method: "DELETE" },
    );
  },
};
