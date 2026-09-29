import { useState } from "react";
import { Button, Copy } from "../common";
import { useDeviceLocation } from "../../store/LocationProvider";
import {
  routingService,
  WalkingRoute,
} from "../../services/location/routingService";
import {
  Coordinate,
  formatDistance,
  formatDuration,
} from "../../utils/geospatial";
export function WalkingRouteSummary({
  destination,
}: {
  destination: Coordinate;
}) {
  const { coordinates } = useDeviceLocation();
  const [result, setResult] = useState<{
    origin: Coordinate;
    route: WalkingRoute | null;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  if (!coordinates) return null;
  const current = result?.origin === coordinates ? result : null;
  return (
    <>
      {current ? (
        <Copy muted>
          {current.route
            ? `${formatDuration(current.route.durationSeconds)} · ${formatDistance(current.route.distanceMeters)} walking route`
            : "Walking route unavailable. Use the straight-line distance above or open Directions."}
        </Copy>
      ) : (
        <Button
          secondary
          label="Check walking route"
          loading={loading}
          onPress={() => {
            setLoading(true);
            void routingService
              .getWalkingRoute(coordinates, destination)
              .then((route) => setResult({ origin: coordinates, route }))
              .finally(() => setLoading(false));
          }}
        />
      )}
    </>
  );
}
