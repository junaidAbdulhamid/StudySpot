import { useCallback } from "react";
import { useLocalSearchParams } from "expo-router";
import { locationService } from "../services/locationService";
import { useAsync } from "./useAsync";
export function useLocation() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return useAsync(useCallback(() => locationService.getLocationById(id), [id]));
}
