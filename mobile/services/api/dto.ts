import { z } from "zod";
const percent = z.number().int().min(0).max(100);
const timestamp = z.string().datetime({ offset: true });
const confidence = z.enum(["low", "medium", "high"]);
const source = z.enum([
  "seed",
  "manual",
  "crowd_report",
  "model",
  "derived",
  "sensor",
]);
export const amenityDto = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
  icon: z.string(),
});
export const predictionDto = z.object({
  id: z.string(),
  location_id: z.string(),
  target_time: timestamp,
  predicted_occupancy: percent,
  confidence,
  source,
  model_version: z.string(),
  created_at: timestamp,
});
export const locationDto = z.object({
  distance_meters: z.number().nonnegative().optional(),
  id: z.string(),
  name: z.string(),
  floor: z.string(),
  description: z.string(),
  capacity: z.number().int().nonnegative(),
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  building: z.object({
    id: z.string(),
    name: z.string(),
    campus_id: z.string(),
  }),
  campus: z.object({
    id: z.string(),
    name: z.string(),
    university_name: z.string(),
    timezone: z.string(),
  }),
  amenities: z.array(amenityDto),
  noise_level: z.enum(["quiet", "moderate", "social"]),
  image_url: z.string().nullable(),
  hours: z.object({
    open: z.string().regex(/^\d{2}:\d{2}$/),
    close: z.string().regex(/^\d{2}:\d{2}$/),
  }),
  current_occupancy: z
    .object({
      id: z.string(),
      percent: percent.nullable(),
      level: z.enum(["available", "moderate", "busy", "full", "unknown"]),
      confidence,
      confidence_score: z.number().min(0).max(1),
      signal_count: z.number().int().nonnegative(),
      source,
      estimated_at: timestamp,
    })
    .nullable(),
  predictions: z.array(predictionDto),
  historical: z.array(
    z.object({ occupancy_percent: percent, observed_at: timestamp, source }),
  ),
});
export const userDto = z.object({
  id: z.string(),
  email: z.string(),
  display_name: z.string(),
  onboarding_completed: z.boolean(),
  avatar_url: z.string().nullable(),
  points: z.number(),
});
export const preferencesDto = z.object({
  id: z.string(),
  user_id: z.string(),
  noise_preference: z.enum(["quiet", "moderate", "social", "any"]),
  study_style: z.enum(["solo", "group", "both"]),
  max_walking_minutes: z.number().positive(),
  study_duration_hours: z.number().positive(),
  preferred_amenities: z.array(amenityDto),
});
export const favoriteDto = z.object({
  id: z.string(),
  user_id: z.string(),
  location_id: z.string(),
  created_at: timestamp,
});
export type LocationDto = z.infer<typeof locationDto>;
export type PredictionDto = z.infer<typeof predictionDto>;
export type PreferencesDto = z.infer<typeof preferencesDto>;
