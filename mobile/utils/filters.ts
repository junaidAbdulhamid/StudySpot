import { LocationFilters, StudyLocation } from "../types";
import { getOccupancyLevel } from "./occupancy";
export const defaultFilters: LocationFilters = {
  query: "",
  maxWalk: 99,
  crowding: "any",
  noise: "any",
  amenities: [],
};
export function filterLocations(
  locations: StudyLocation[],
  filters: LocationFilters,
) {
  const query = filters.query.trim().toLowerCase();
  return locations.filter(
    (l) =>
      `${l.name} ${l.building} ${l.floor} ${l.amenities.join(" ")}`
        .toLowerCase()
        .includes(query) &&
      (l.walkingMinutes === null || l.walkingMinutes <= filters.maxWalk) &&
      (filters.crowding === "any" ||
        getOccupancyLevel(l.currentOccupancy) === filters.crowding) &&
      (filters.noise === "any" || l.noiseLevel === filters.noise) &&
      filters.amenities.every((a) => l.amenities.includes(a)),
  );
}
