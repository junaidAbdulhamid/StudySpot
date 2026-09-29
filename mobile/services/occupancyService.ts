import { z } from "zod";
import { apiClient, dataSchema } from "./api/client";

const timestamp = z.string().datetime({ offset: true });
const checkInDto = z.object({
  id: z.string(),
  location_id: z.string(),
  status: z.enum(["active", "completed", "expired"]),
  checked_in_at: timestamp,
  checked_out_at: timestamp.nullable(),
  expires_at: timestamp,
  location_verified: z.boolean(),
});
const contributionDto = z.object({
  id: z.string(),
  location_id: z.string(),
  submitted_at: timestamp,
});
const currentDto = z.object({
  location_id: z.string(),
  estimate_id: z.string().nullable(),
  occupancy_percent: z.number().int().min(0).max(100).nullable(),
  occupancy_level: z.enum(["available", "moderate", "busy", "full", "unknown"]),
  confidence: z.object({
    score: z.number(),
    label: z.enum(["low", "medium", "high"]),
  }),
  updated_at: timestamp.nullable(),
  freshness_seconds: z.number().int().nullable(),
  signal_count: z.number().int(),
  signal_summary: z.object({
    recent_reports: z.number().int(),
    active_checkins: z.number().int(),
    recent_validations: z.number().int(),
    trusted_observation: z.boolean(),
  }),
});
export type ActiveCheckIn = z.infer<typeof checkInDto>;
export type CurrentOccupancy = z.infer<typeof currentDto>;
export type CrowdLevel = "lots_of_seats" | "moderate" | "busy" | "nearly_full";
type Coordinates = { latitude: number; longitude: number } | null;
const position = (coordinates: Coordinates) =>
  coordinates
    ? { latitude: coordinates.latitude, longitude: coordinates.longitude }
    : {};
export const occupancyService = {
  async activeCheckIn() {
    return (
      await apiClient.request(
        "/me/checkins/active",
        dataSchema(checkInDto.nullable()),
      )
    ).data;
  },
  async checkIn(locationId: string, coordinates: Coordinates) {
    return (
      await apiClient.request("/checkins", dataSchema(checkInDto), {
        method: "POST",
        body: { location_id: locationId, ...position(coordinates) },
      })
    ).data;
  },
  async checkOut(checkinId: string) {
    return (
      await apiClient.request(
        `/checkins/${encodeURIComponent(checkinId)}/checkout`,
        dataSchema(checkInDto),
        { method: "POST" },
      )
    ).data;
  },
  async submitReport(
    locationId: string,
    crowdLevel: CrowdLevel,
    coordinates: Coordinates,
  ) {
    return (
      await apiClient.request("/crowd-reports", dataSchema(contributionDto), {
        method: "POST",
        body: {
          location_id: locationId,
          crowd_level: crowdLevel,
          ...position(coordinates),
        },
      })
    ).data;
  },
  async validate(
    locationId: string,
    estimateId: string,
    kind: "accurate" | "more_crowded" | "less_crowded",
    coordinates: Coordinates,
  ) {
    return (
      await apiClient.request(
        "/occupancy-validations",
        dataSchema(contributionDto),
        {
          method: "POST",
          body: {
            location_id: locationId,
            estimate_id: estimateId,
            validation_type: kind,
            ...position(coordinates),
          },
        },
      )
    ).data;
  },
  async current(locationId: string) {
    return (
      await apiClient.request(
        `/locations/${encodeURIComponent(locationId)}/occupancy`,
        dataSchema(currentDto),
      )
    ).data;
  },
};
