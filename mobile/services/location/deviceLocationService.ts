import * as Location from "expo-location";
import { Position } from "../../utils/geospatial";
export const deviceLocationService = {
  permission: () => Location.getForegroundPermissionsAsync(),
  request: () => Location.requestForegroundPermissionsAsync(),
  async current(): Promise<Position> {
    if (!(await Location.hasServicesEnabledAsync()))
      throw new Error(
        "Location services are disabled. You can still browse campus.",
      );
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      const position = await Promise.race([
        Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        }),
        new Promise<never>((_, reject) => {
          timer = setTimeout(
            () =>
              reject(
                new Error(
                  "Location timed out. Try again outdoors or browse campus.",
                ),
              ),
            15000,
          );
        }),
      ]);
      return {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        timestamp: position.timestamp,
      };
    } finally {
      clearTimeout(timer);
    }
  },
};
