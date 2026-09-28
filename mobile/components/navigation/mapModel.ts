import { StudyLocation } from "../../types";
import { Coordinate } from "../../utils/geospatial";
export const mapToken = process.env.EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN ?? "";
export interface CampusMapProps {
  locations: StudyLocation[];
  selectedId: string | null;
  onSelect(id: string): void;
  center?: Coordinate | null;
  position?: Coordinate | null;
  recenter?: number;
}
export function mapGroups(locations: StudyLocation[]) {
  const groups = new Map<string, StudyLocation[]>();
  for (const location of locations) {
    const key = location.buildingId ?? location.building;
    groups.set(key, [...(groups.get(key) ?? []), location]);
  }
  return [...groups].map(([id, rows]) => ({
    id,
    locations: rows,
    best: [...rows].sort(
      (a, b) => (a.currentOccupancy ?? 101) - (b.currentOccupancy ?? 101),
    )[0]!,
  }));
}
