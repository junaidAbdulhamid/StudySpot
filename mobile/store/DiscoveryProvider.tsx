import {
  createContext,
  useContext,
  useState,
  ReactNode,
  Dispatch,
  SetStateAction,
  useCallback,
} from "react";
import { LocationFilters } from "../types";
import { defaultFilters } from "../utils/filters";
import { useDeviceLocation } from "./LocationProvider";
import { locationService } from "../services/locationService";
import { useAsync } from "../hooks/useAsync";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { campusService } from "../services/campusService";
const Context = createContext<{
  filters: LocationFilters;
  setFilters: Dispatch<SetStateAction<LocationFilters>>;
} | null>(null);
export function DiscoveryProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState(defaultFilters);
  return (
    <Context.Provider value={{ filters, setFilters }}>
      {children}
    </Context.Provider>
  );
}
export function useDiscoveryFilters() {
  const context = useContext(Context);
  if (!context) throw new Error("DiscoveryProvider missing");
  return context;
}
export function useDiscovery() {
  const { filters, setFilters } = useDiscoveryFilters();
  const debounced = useDebouncedValue(filters);
  const { coordinates } = useDeviceLocation();
  const loader = useCallback(async () => {
    const campusId =
      debounced.campusId ?? (await campusService.getCampuses())[0]?.id;
    if (!campusId) return [];
    const rows = coordinates
      ? await locationService.getNearbyLocations(
          coordinates.latitude,
          coordinates.longitude,
          { ...debounced, campusId },
        )
      : (
          await locationService.getLocationPage(
            { ...debounced, campusId },
            1,
            100,
          )
        ).items;
    return coordinates && debounced.nearest
      ? rows
      : rows.sort(
          (a, b) =>
            a.name.localeCompare(b.name) || a.floor.localeCompare(b.floor),
        );
  }, [coordinates, debounced]);
  return { ...useAsync(loader), filters, setFilters };
}
