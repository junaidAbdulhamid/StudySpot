import { Pressable, View } from "react-native";
import { StudyLocation } from "../../types";
import { colors as c, radius as r, spacing as s } from "../../theme";
import { Copy, Icon } from "../common";
import {
  getOccupancyColor,
  getOccupancyLevel,
  formatOccupancy,
} from "../../utils/occupancy";
export interface CampusMapProps {
  locations: StudyLocation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  showPosition?: boolean;
}
// The screen depends only on this contract. A future native map provider can replace the schematic.
export function CampusMap({
  locations,
  selectedId,
  onSelect,
  showPosition = true,
}: CampusMapProps) {
  return (
    <View
      style={{
        height: 380,
        overflow: "hidden",
        borderRadius: r.lg,
        backgroundColor: c.surface,
        borderWidth: 1,
        borderColor: c.border,
      }}
    >
      <View
        style={{
          position: "absolute",
          left: "15%",
          top: 0,
          width: 24,
          height: "100%",
          backgroundColor: c.mapRoad,
          transform: [{ rotate: "-15deg" }],
        }}
      />
      <View
        style={{
          position: "absolute",
          left: 0,
          top: "46%",
          height: 22,
          width: "110%",
          backgroundColor: c.mapRoad,
          transform: [{ rotate: "12deg" }],
        }}
      />
      <View
        style={{
          position: "absolute",
          right: "21%",
          top: 0,
          width: 14,
          height: "100%",
          backgroundColor: c.mapRoad,
          transform: [{ rotate: "22deg" }],
        }}
      />
      {[
        { left: 34, top: 13, width: 29, height: 22 },
        { left: 5, top: 60, width: 26, height: 28 },
        { left: 52, top: 59, width: 32, height: 26 },
      ].map((b, i) => (
        <View
          key={i}
          style={{
            position: "absolute",
            left: `${b.left}%`,
            top: `${b.top}%`,
            width: `${b.width}%`,
            height: `${b.height}%`,
            backgroundColor: c.mapGreen,
            borderRadius: r.md,
            borderWidth: 1,
            borderColor: c.border,
          }}
        />
      ))}
      <View style={{ position: "absolute", left: "36%", top: "37%" }}>
        <Copy variant="label" muted>
          MASON CAMPUS
        </Copy>
      </View>
      {locations.map((l, index) => {
        const left = 8 + (index % 4) * 23;
        const top = 8 + Math.floor(index / 4) * 29;
        const selected = l.id === selectedId;
        const color = getOccupancyColor(getOccupancyLevel(l.currentOccupancy));
        return (
          <Pressable
            key={l.id}
            accessibilityRole="button"
            accessibilityLabel={`${l.name}, ${l.floor}, ${formatOccupancy(l.currentOccupancy)} ${getOccupancyLevel(l.currentOccupancy)}`}
            accessibilityState={{ selected }}
            onPress={() => onSelect(l.id)}
            style={({ pressed }) => ({
              position: "absolute",
              left: `${left}%`,
              top: `${top}%`,
              minWidth: 48,
              minHeight: 44,
              borderRadius: r.pill,
              padding: s.sm,
              backgroundColor: selected ? color : c.background,
              borderWidth: 2,
              borderColor: color,
              alignItems: "center",
              justifyContent: "center",
              opacity: pressed ? 0.7 : 1,
            })}
          >
            <Copy
              variant="caption"
              color={selected ? c.background : color}
              style={{ fontWeight: "700" }}
            >
              {formatOccupancy(l.currentOccupancy)}
            </Copy>
          </Pressable>
        );
      })}
      {showPosition && (
        <View
          accessibilityLabel="Demo starting point"
          style={{
            position: "absolute",
            bottom: 18,
            left: "43%",
            padding: 8,
            borderRadius: 30,
            borderWidth: 6,
            borderColor: c.surfaceElevated,
            backgroundColor: c.primary,
          }}
        >
          <Icon name="navigate" size={16} color={c.background} />
        </View>
      )}
    </View>
  );
}
