import { colors } from "../theme/colors";
import { OccupancyLevel } from "../types";
export function getOccupancyLevel(percent: number | null): OccupancyLevel {
  if (percent === null || !Number.isFinite(percent)) return "unknown";
  const p = Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
  return p < 40 ? "available" : p < 65 ? "moderate" : p < 85 ? "busy" : "full";
}
export const occupancyLabels: Record<OccupancyLevel, string> = {
  available: "Available",
  moderate: "Moderate",
  busy: "Busy",
  full: "Nearly full",
  unknown: "Unavailable",
};
export const getOccupancyLabel = (percent: number | null) =>
  occupancyLabels[getOccupancyLevel(percent)];
export const getOccupancyColor = (level: OccupancyLevel) =>
  ({
    available: colors.occupancyAvailable,
    moderate: colors.occupancyModerate,
    busy: colors.occupancyBusy,
    full: colors.occupancyFull,
    unknown: colors.textMuted,
  })[level];
export const formatWalkingDistance = (minutes: number | null) =>
  minutes === null ? "Distance unavailable" : `${minutes} min walk`;
export const formatOccupancy = (percent: number | null) =>
  percent === null ? "—" : `${percent}%`;
export const formatEstimateAge = (timestamp?: string) =>
  !timestamp
    ? "Unavailable"
    : `${Math.max(0, Math.floor((Date.now() - Date.parse(timestamp)) / 60000))} min ago`;
export function formatOperatingHours(hours: { open: string; close: string }) {
  const format = (value: string) => {
    const [hour = "0", minute = "00"] = value.split(":");
    const h = Number(hour);
    return `${h % 12 || 12}:${minute} ${h >= 12 ? "PM" : "AM"}`;
  };
  return `${format(hours.open)} – ${format(hours.close)}`;
}
