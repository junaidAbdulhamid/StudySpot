import { memo, useEffect, useRef, useState } from "react";
import { Pressable, View } from "react-native";
import {
  Camera,
  CameraRef,
  Map,
  Marker,
} from "@maplibre/maplibre-react-native";
import { Copy } from "../common";
import { colors } from "../../theme";
import { CampusMapProps, mapGroups, mapStyleUrl } from "./mapModel";
import {
  getOccupancyColor,
  getOccupancyLevel,
  formatOccupancy,
} from "../../utils/occupancy";

export const CampusMap = memo(function CampusMap({
  locations,
  selectedId,
  onSelect,
  center,
  position,
  recenter = 0,
}: CampusMapProps) {
  const camera = useRef<CameraRef>(null);
  const [error, setError] = useState(false);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    if (center)
      camera.current?.easeTo({
        center: [center.longitude, center.latitude],
        zoom: 15,
        duration: 700,
      });
  }, [center, recenter]);
  if (!center) return <Copy>Loading campus map configuration…</Copy>;
  return (
    <View style={{ height: 400, borderRadius: 20, overflow: "hidden" }}>
      <Map
        style={{ flex: 1 }}
        mapStyle={mapStyleUrl}
        onDidFinishLoadingMap={() => setLoaded(true)}
        onDidFailLoadingMap={() => setError(true)}
      >
        <Camera
          ref={camera}
          initialViewState={{
            center: [center.longitude, center.latitude],
            zoom: 15,
          }}
        />
        {mapGroups(locations).map((group) => {
          const selected = group.locations.some((l) => l.id === selectedId);
          const level = getOccupancyLevel(group.best.currentOccupancy);
          return (
            <Marker
              key={group.id}
              id={group.id}
              lngLat={[group.best.longitude, group.best.latitude]}
              onPress={() => onSelect(group.best.id)}
            >
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={`${group.best.building}, ${level}, ${formatOccupancy(group.best.currentOccupancy)}, ${group.locations.length} study zones`}
                onPress={() => onSelect(group.best.id)}
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
            </Marker>
          );
        })}
        {position && (
          <Marker
            id="current-position"
            lngLat={[position.longitude, position.latitude]}
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
          </Marker>
        )}
      </Map>
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
          Map could not load. Check your connection or map style. Study spaces
          remain available below.
        </Copy>
      )}
    </View>
  );
});
