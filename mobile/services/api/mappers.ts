import {
  Amenity,
  OccupancyPrediction,
  StudyLocation,
  UserPreferences,
} from "../../types";
import { LocationDto, PredictionDto, PreferencesDto } from "./dto";
export const amenitySlugs: Record<Amenity, string> = {
  Outlets: "outlets",
  Whiteboards: "whiteboards",
  "Large tables": "large-tables",
  "Food nearby": "food-nearby",
  Printers: "printers",
  "Natural light": "natural-light",
  "Group rooms": "group-rooms",
  "Quiet zone": "quiet-zone",
};
function mapAmenities(amenities: { slug: string }[]): Amenity[] {
  return (Object.keys(amenitySlugs) as Amenity[]).filter((name) =>
    amenities.some((a) => a.slug === amenitySlugs[name]),
  );
}
export function mapPredictionDto(
  dto: PredictionDto,
  now = Date.now(),
): OccupancyPrediction {
  return {
    label: new Date(dto.target_time).toLocaleTimeString([], {
      hour: "numeric",
    }),
    hoursAhead: Math.max(0, (Date.parse(dto.target_time) - now) / 3600000),
    percent: dto.predicted_occupancy,
    targetTime: dto.target_time,
    source: dto.source,
  };
}
export function mapLocationDtoToStudyLocation(dto: LocationDto): StudyLocation {
  return {
    id: dto.id,
    name: dto.name,
    building: dto.building.name,
    floor: dto.floor,
    latitude: dto.latitude,
    longitude: dto.longitude,
    capacity: dto.capacity,
    noiseLevel: dto.noise_level,
    amenities: mapAmenities(dto.amenities),
    currentOccupancy: dto.current_occupancy?.percent ?? null,
    occupancyConfidence: dto.current_occupancy?.confidence ?? null,
    estimatedAt: dto.current_occupancy?.estimated_at,
    occupancySource: dto.current_occupancy?.source,
    walkingMinutes: null,
    isFavorite: false,
    image: dto.building.name.includes("Library")
      ? "library"
      : dto.building.name.includes("Johnson") || dto.building.name === "SUB I"
        ? "commons"
        : "hall",
    imageUrl: dto.image_url,
    description: dto.description,
    hours: dto.hours,
    predictions: dto.predictions.map((p) => mapPredictionDto(p)),
    historical: dto.historical.map((h) => h.occupancy_percent),
    historicalLabels: dto.historical.map((h) =>
      new Date(h.observed_at).toLocaleTimeString([], { hour: "numeric" }),
    ),
  };
}
export function mapPreferencesDto(dto: PreferencesDto): UserPreferences {
  return {
    noise: dto.noise_preference,
    studyType: dto.study_style === "both" ? "either" : dto.study_style,
    amenities: mapAmenities(dto.preferred_amenities),
    maxWalk: dto.max_walking_minutes,
    duration: dto.study_duration_hours,
  };
}
export function preferencesToDto(value: UserPreferences) {
  return {
    noise_preference: value.noise,
    study_style:
      value.studyType === "either" ? ("both" as const) : value.studyType,
    preferred_amenities: value.amenities.map((a) => amenitySlugs[a]),
    max_walking_minutes: value.maxWalk,
    study_duration_hours: value.duration,
  };
}
