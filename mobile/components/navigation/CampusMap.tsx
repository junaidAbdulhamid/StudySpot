import { memo, useEffect, useRef, useState } from "react";
import { View, Pressable } from "react-native";
import Mapbox from "@rnmapbox/maps";
import { Copy } from "../common";
import { colors } from "../../theme";
import { CampusMapProps, mapGroups, mapToken } from "./mapModel";
import {
  getOccupancyColor,
  getOccupancyLevel,
  formatOccupancy,
} from "../../utils/occupancy";
if (mapToken) {
  Mapbox.setAccessToken(mapToken);
  Mapbox.setTelemetryEnabled(false);
}
export const CampusMap = memo(function CampusMap({
  locations,
  selectedId,
  onSelect,
  center,
  position,
  recenter = 0,
}: CampusMapProps) {
  const camera = useRef<Mapbox.Camera>(null);
  const [error, setError] = useState(false);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    if (center)
      camera.current?.setCamera({
        centerCoordinate: [center.longitude, center.latitude],
        zoomLevel: 15,
        animationDuration: 700,
      });
  }, [center, recenter]);
  if (!mapToken)
    return (
      <Copy>
        Map setup required: set EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN and restart the
        development build. Browse spaces below while maps are unavailable.
      </Copy>
    );
  if (!center) return <Copy>Loading campus map configuration…</Copy>;
  return (
    <View style={{ height: 400, borderRadius: 20, overflow: "hidden" }}>
      <Mapbox.MapView
        style={{ flex: 1 }}
        styleURL={Mapbox.StyleURL.Dark}
        onMapLoadingError={() => setError(true)}
        onDidFinishLoadingMap={() => setLoaded(true)}
      >
        <Mapbox.Camera
          ref={camera}
          defaultSettings={{
            centerCoordinate: [center.longitude, center.latitude],
            zoomLevel: 15,
          }}
        />
        {mapGroups(locations).map((group) => {
          const selected = group.locations.some((l) => l.id === selectedId);
          const level = getOccupancyLevel(group.best.currentOccupancy);
          return (
            <Mapbox.MarkerView
              key={group.id}
              coordinate={[group.best.longitude, group.best.latitude]}
            >
              <Pressable
                onPress={() => onSelect(group.best.id)}
                accessibilityRole="button"
                accessibilityLabel={`${group.best.building}, ${level}, ${formatOccupancy(group.best.currentOccupancy)}, ${group.locations.length} study zones`}
                style={{
                  backgroundColor: colors.background,
                  borderWidth: selected ? 3 : 1,
                  borderColor: getOccupancyColor(level),
                  padding: 8,
                  borderRadius: 12,
                }}
              >
                <Copy>
                  {group.best.building} ·{" "}
                  {formatOccupancy(group.best.currentOccupancy)} {level}
                </Copy>
              </Pressable>
            </Mapbox.MarkerView>
          );
        })}
        {position && (
          <Mapbox.PointAnnotation
            id="current-position"
            coordinate={[position.longitude, position.latitude]}
          >
            <View
              accessibilityLabel="Your approximate location"
              style={{
                width: 20,
                height: 20,
                borderRadius: 10,
                backgroundColor: "#5DAAFF",
                borderWidth: 3,
                borderColor: "white",
              }}
            />
          </Mapbox.PointAnnotation>
        )}
      </Mapbox.MapView>
      {!loaded && !error && (
        <Copy
          style={{
            position: "absolute",
            top: 8,
            left: 8,
            backgroundColor: colors.background,
          }}
        >
          Loading campus map…
        </Copy>
      )}
      {error && (
        <Copy>
          Map could not load. Check your connection and map token. Study spaces
          remain available below.
        </Copy>
      )}
    </View>
  );
});
