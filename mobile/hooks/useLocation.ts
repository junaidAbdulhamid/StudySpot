import { useCallback } from "react";
import { useLocalSearchParams } from "expo-router";
import { locationService } from "../services/locationService";
import { useAsync } from "./useAsync";
import { useDeviceLocation } from "../store/LocationProvider";
import { straightLineDistance } from "../utils/geospatial";
export function useLocation() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { coordinates } = useDeviceLocation();
  const state = useAsync(
    useCallback(() => locationService.getLocationById(id), [id]),
  );
  return {
    ...state,
    data:
      state.data && coordinates
        ? {
            ...state.data,
            distanceMeters: straightLineDistance(coordinates, state.data),
          }
        : state.data,
  };
}
