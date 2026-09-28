import { LocationFilters, OccupancyPrediction, StudyLocation } from "../types";
import {
  ApiError,
  ApiPage,
  apiClient,
  collectPages,
  dataSchema,
  pageSchema,
} from "./api/client";
import { locationDto, predictionDto } from "./api/dto";
import {
  amenitySlugs,
  mapLocationDtoToStudyLocation,
  mapPredictionDto,
} from "./api/mappers";
import { z } from "zod";
export interface LocationService {
  getNearbyLocations(
    latitude: number,
    longitude: number,
    filters?: Partial<LocationFilters>,
  ): Promise<StudyLocation[]>;
  getLocations(): Promise<StudyLocation[]>;
  getLocationPage(
    filters?: Partial<LocationFilters>,
    page?: number,
    pageSize?: number,
    signal?: AbortSignal,
  ): Promise<ApiPage<StudyLocation>>;
  getLocationById(id: string): Promise<StudyLocation | undefined>;
  getPredictions(
    id: string,
    hoursAhead?: number,
  ): Promise<OccupancyPrediction[]>;
}
export const locationService: LocationService = {
  async getNearbyLocations(latitude, longitude, filters = {}) {
    const query = filterQuery(filters);
    query.set("latitude", String(latitude));
    query.set("longitude", String(longitude));
    query.set("radius_meters", String(filters.radiusMeters ?? 1500));
    query.set("limit", "100");
    const result = await apiClient.request(
      `/locations/nearby?${query}`,
      dataSchema(z.array(locationDto)),
    );
    return result.data.map(mapLocationDtoToStudyLocation);
  },
  async getLocationPage(filters = {}, page = 1, pageSize = 20, signal) {
    const query = filterQuery(filters);
    query.set("page", String(page));
    query.set("page_size", String(pageSize));
    const result = await apiClient.request(
      `/locations?${query}`,
      pageSchema(locationDto),
      { signal },
    );
    return {
      ...result,
      items: result.items.map(mapLocationDtoToStudyLocation),
    };
  },
  async getLocations() {
    return collectPages((page) =>
      locationService.getLocationPage({}, page, 100),
    );
  },
  async getLocationById(id) {
    try {
      const result = await apiClient.request(
        `/locations/${encodeURIComponent(id)}`,
        dataSchema(locationDto),
      );
      return mapLocationDtoToStudyLocation(result.data);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return undefined;
      throw error;
    }
  },
  async getPredictions(id, hoursAhead = 4) {
    const result = await apiClient.request(
      `/locations/${encodeURIComponent(id)}/predictions?hours_ahead=${hoursAhead}`,
      dataSchema(z.array(predictionDto)),
    );
    return result.data.map((p) => mapPredictionDto(p));
  },
};

export function filterQuery(filters: Partial<LocationFilters>) {
  const query = new URLSearchParams();
  if (filters.query?.trim()) query.set("search", filters.query.trim());
  if (filters.noise && filters.noise !== "any")
    query.set("noise_level", filters.noise);
  if (filters.amenities?.length)
    query.set(
      "amenities",
      filters.amenities.map((a) => amenitySlugs[a]).join(","),
    );
  if (filters.campusId) query.set("campus_id", filters.campusId);
  if (filters.buildingId) query.set("building_id", filters.buildingId);
  if (filters.openNow) query.set("open_now", "true");
  const ranges = {
    available: [0, 39],
    moderate: [40, 64],
    busy: [65, 84],
    full: [85, 100],
  };
  if (
    filters.crowding &&
    filters.crowding !== "any" &&
    filters.crowding !== "unknown"
  ) {
    const range = ranges[filters.crowding];
    query.set("min_occupancy", String(range[0]));
    query.set("max_occupancy", String(range[1]));
  }
  return query;
}
