import React from "react";
import { View } from "react-native";
import { colors as c, radius as r, spacing as s } from "../../theme";
import {
  getOccupancyColor,
  formatOccupancy,
  getOccupancyLabel,
  getOccupancyLevel,
} from "../../utils/occupancy";
import { Card, Copy, Icon } from "../common";
export function OccupancyBadge({ percent }: { percent: number | null }) {
  const color = getOccupancyColor(getOccupancyLevel(percent));
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: s.sm }}>
      <View
        style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: color }}
      />
      <Copy variant="caption" color={color} style={{ fontWeight: "600" }}>
        {formatOccupancy(percent)} · {getOccupancyLabel(percent)}
      </Copy>
    </View>
  );
}
export function OccupancyBar({ percent }: { percent: number | null }) {
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityLabel="Occupancy"
      accessibilityValue={{ min: 0, max: 100, now: percent ?? undefined }}
      style={{
        height: 8,
        borderRadius: r.pill,
        backgroundColor: c.border,
        overflow: "hidden",
      }}
    >
      <View
        style={{
          height: "100%",
          width: `${Math.min(100, Math.max(0, percent ?? 0))}%`,
          backgroundColor: getOccupancyColor(getOccupancyLevel(percent)),
          borderRadius: r.pill,
        }}
      />
    </View>
  );
}
export const CrowdIndicator = OccupancyBadge;
export function PredictionBadge({ percent }: { percent: number | null }) {
  return (
    <View style={{ flexDirection: "row", gap: s.sm, alignItems: "center" }}>
      <Icon name="trending-up-outline" size={16} color={c.textSecondary} />
      <Copy muted variant="caption">
        {percent === null
          ? "No future forecast available"
          : `Seed forecast: ${formatOccupancy(percent)} occupied`}
      </Copy>
    </View>
  );
}
export function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card style={{ flex: 1 }}>
      <Copy muted variant="caption">
        {label}
      </Copy>
      <Copy variant="heading">{value}</Copy>
    </Card>
  );
}
export function OccupancyMeter({ percent }: { percent: number | null }) {
  const color = getOccupancyColor(getOccupancyLevel(percent));
  return (
    <View
      style={{
        alignSelf: "center",
        width: 208,
        height: 208,
        borderRadius: 104,
        borderWidth: 12,
        borderColor: c.border,
        alignItems: "center",
        justifyContent: "center",
        marginVertical: s.xl,
      }}
    >
      <Copy
        style={{ fontSize: 56, fontWeight: "700", letterSpacing: -3 }}
        color={color}
      >
        {formatOccupancy(percent)}
      </Copy>
      <Copy muted>{getOccupancyLabel(percent)}</Copy>
    </View>
  );
}
export function BarChart({
  points,
  label,
}: {
  points: { label: string; percent: number }[];
  label: string;
}) {
  return (
    <View
      accessibilityLabel={label}
      style={{
        flexDirection: "row",
        gap: s.md,
        alignItems: "flex-end",
        paddingTop: s.xl,
      }}
    >
      {points.map((p, i) => (
        <View
          key={`${p.label}-${i}`}
          style={{ flex: 1, alignItems: "center", gap: s.sm }}
        >
          <Copy variant="caption" muted>
            {p.percent}%
          </Copy>
          <View
            style={{
              height: 125,
              width: "100%",
              justifyContent: "flex-end",
              backgroundColor: c.background,
              borderRadius: r.sm,
              overflow: "hidden",
            }}
          >
            <View
              style={{
                height: `${p.percent}%`,
                minHeight: 4,
                backgroundColor: getOccupancyColor(
                  getOccupancyLevel(p.percent),
                ),
                borderRadius: r.sm,
              }}
            />
          </View>
          <Copy variant="caption" muted>
            {p.label}
          </Copy>
        </View>
      ))}
    </View>
  );
}
