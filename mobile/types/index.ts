export type NoiseLevel = "quiet" | "moderate" | "social";
export type Amenity =
  | "Outlets"
  | "Whiteboards"
  | "Large tables"
  | "Food nearby"
  | "Printers"
  | "Natural light"
  | "Group rooms"
  | "Quiet zone";
export type OccupancyLevel =
  "available" | "moderate" | "busy" | "full" | "unknown";
export interface Campus {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
}
export interface Building {
  id: string;
  name: string;
  campusId: string;
}
export interface UserPreferences {
  noise: NoiseLevel | "any";
  studyType: "solo" | "group" | "either";
  amenities: Amenity[];
  maxWalk: number;
  duration: number;
}
export interface User {
  id: string;
  name: string;
  email: string;
  preferences: UserPreferences;
}
export interface OccupancyEstimate {
  percent: number;
  confidence: "low" | "medium" | "high";
  updatedMinutesAgo: number;
}
export interface OccupancyPrediction {
  label: string;
  hoursAhead: number;
  percent: number;
  targetTime?: string;
  source?: string;
}
export interface StudyLocation {
  id: string;
  name: string;
  building: string;
  floor: string;
  latitude: number;
  longitude: number;
  capacity: number;
  noiseLevel: NoiseLevel;
  amenities: Amenity[];
  currentOccupancy: number | null;
  estimatedAt?: string;
  occupancySource?: string;
  imageUrl?: string | null;
  historicalLabels?: string[];
  occupancyConfidence: OccupancyEstimate["confidence"] | null;
  walkingMinutes: number | null;
  isFavorite: boolean;
  image: "library" | "hall" | "commons";
  description: string;
  hours: { open: string; close: string };
  predictions: OccupancyPrediction[];
  historical: number[];
}
export interface CrowdReport {
  locationId: string;
  level: OccupancyLevel;
  createdAt: string;
}
export interface Recommendation {
  location: StudyLocation;
  score: number;
  reasons: string[];
  expectedOccupancy: number | null;
}
export interface Alert {
  id: string;
  locationId: string;
  title: string;
  message: string;
  timestamp: string;
  percent: number;
}
export interface LocationFilters {
  campusId?: string;
  buildingId?: string;
  query: string;
  maxWalk: number;
  crowding: OccupancyLevel | "any";
  noise: NoiseLevel | "any";
  amenities: Amenity[];
}
