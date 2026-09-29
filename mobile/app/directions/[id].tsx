import { useCallback, useState } from "react";
import {
  Button,
  Card,
  Copy,
  Screen,
  ScreenHeader,
} from "../../components/common";
import { LocationBoundary } from "../../components/location/LocationBoundary";
import { useLocation } from "../../hooks/useLocation";
import { useAsync } from "../../hooks/useAsync";
import { useDeviceLocation } from "../../store/LocationProvider";
import { routingService } from "../../services/location/routingService";
import { openDirections } from "../../services/location/directionsService";
import {
  distanceLabel,
  formatDistance,
  formatDuration,
} from "../../utils/geospatial";
export default function Directions() {
  const state = useLocation();
  const { coordinates } = useDeviceLocation();
  const latitude = state.data?.latitude;
  const longitude = state.data?.longitude;
  const route = useAsync(
    useCallback(
      () =>
        coordinates && latitude != null && longitude != null
          ? routingService.getWalkingRoute(coordinates, { latitude, longitude })
          : Promise.resolve(null),
      [coordinates, latitude, longitude],
    ),
  );
  const [error, setError] = useState<string | null>(null);
  return (
    <LocationBoundary state={state}>
      {(location) => (
        <Screen>
          <ScreenHeader
            title="Your next stop."
            subtitle={`${location.name} · ${location.floor}`}
            back
          />
          <Card>
            <Copy variant="heading">
              {route.data
                ? `${formatDuration(route.data.durationSeconds)} · ${formatDistance(route.data.distanceMeters)} walking route`
                : distanceLabel(location)}
            </Copy>
            <Copy muted>
              {route.loading
                ? "Checking walking route…"
                : route.data
                  ? "Walking route supplied by the configured route provider. Indoor access and floor navigation are not included."
                  : "Walking route unavailable. You can open directions in your maps app."}
            </Copy>
            <Button
              label="Open walking directions"
              onPress={() => {
                void openDirections(location).catch(() =>
                  setError(
                    "Could not open maps. Try again with a browser or maps app installed.",
                  ),
                );
              }}
            />
            {error && <Copy>{error}</Copy>}
            <Copy muted>
              Directions open an external maps provider. Your device and that
              provider control location use there.
            </Copy>
          </Card>
        </Screen>
      )}
    </LocationBoundary>
  );
}
