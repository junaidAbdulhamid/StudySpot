import { Position } from "../../utils/geospatial";
export const LOCATION_TTL = 120000;
export type Permission =
  "unknown" | "requesting" | "granted" | "denied" | "unavailable";
export interface LocationState {
  permissionStatus: Permission;
  coordinates: Position | null;
  isLoading: boolean;
  error: string | null;
}
export interface DeviceLocationAdapter {
  permission(): Promise<{ granted: boolean }>;
  request(): Promise<{ granted: boolean }>;
  current(): Promise<Position>;
}
export function createLocationController(
  adapter: DeviceLocationAdapter,
  notify: (state: LocationState) => void,
  now = Date.now,
) {
  let state: LocationState = {
    permissionStatus: "unknown",
    coordinates: null,
    isLoading: false,
    error: null,
  };
  let generation = 0;
  const publish = (patch: Partial<LocationState>) => {
    state = { ...state, ...patch };
    notify(state);
  };
  return {
    getState: () => state,
    clear() {
      generation++;
      publish({ coordinates: null, isLoading: false });
    },
    async acquire(request: boolean) {
      if (state.isLoading) return;
      const version = generation;
      publish({
        isLoading: true,
        error: null,
        ...(request ? { permissionStatus: "requesting" as const } : {}),
      });
      try {
        const permission = await (request
          ? adapter.request()
          : adapter.permission());
        if (generation !== version) return;
        if (!permission.granted) {
          publish({
            permissionStatus: "denied",
            coordinates: null,
            error:
              "Enable location in device settings to see what’s closest. Campus browsing is still available.",
          });
          return;
        }
        publish({ permissionStatus: "granted" });
        if (
          state.coordinates &&
          now() - state.coordinates.timestamp < LOCATION_TTL
        )
          return;
        const position = await adapter.current();
        if (generation !== version) return;
        if (
          !Number.isFinite(position.latitude) ||
          !Number.isFinite(position.longitude) ||
          Math.abs(position.latitude) > 90 ||
          Math.abs(position.longitude) > 180 ||
          now() - position.timestamp > LOCATION_TTL
        )
          throw new Error("Invalid or expired location");
        publish({
          coordinates: position,
          error:
            position.accuracy != null && position.accuracy > 200
              ? "Your location is approximate; distances may be less accurate indoors."
              : null,
        });
      } catch {
        if (generation === version)
          publish({
            permissionStatus: "unavailable",
            coordinates: null,
            error:
              "Could not get your location. Check location services and try again, or browse campus.",
          });
      } finally {
        if (generation === version) publish({ isLoading: false });
      }
    },
  };
}
