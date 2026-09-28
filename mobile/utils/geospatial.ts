export interface Coordinate {
  latitude: number;
  longitude: number;
}
export interface Position extends Coordinate {
  accuracy: number | null;
  timestamp: number;
}
export function formatDistance(meters?: number | null) {
  if (meters == null || !Number.isFinite(meters)) return "Distance unavailable";
  return meters < 1000
    ? `${Math.round(meters)} m`
    : `${(meters / 1000).toFixed(1)} km`;
}
export function formatDuration(seconds: number) {
  return `${Math.max(1, Math.round(seconds / 60))} min walk`;
}
export function straightLineDistance(a: Coordinate, b: Coordinate) {
  const rad = Math.PI / 180;
  const h =
    Math.sin(((b.latitude - a.latitude) * rad) / 2) ** 2 +
    Math.cos(a.latitude * rad) *
      Math.cos(b.latitude * rad) *
      Math.sin(((b.longitude - a.longitude) * rad) / 2) ** 2;
  return (
    6371008.8 * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(Math.max(0, 1 - h)))
  );
}
export function distanceLabel(location: {
  distanceMeters?: number;
  walkingDurationSeconds?: number;
}) {
  return location.walkingDurationSeconds != null
    ? formatDuration(location.walkingDurationSeconds)
    : location.distanceMeters != null
      ? `${formatDistance(location.distanceMeters)} away · straight-line`
      : "Enable location for distance";
}
export function isLocationOpen(
  hours: { open: string; close: string },
  timezone: string,
  now = new Date(),
) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: timezone,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(now);
  return (
    hours.open === hours.close ||
    (hours.open < hours.close
      ? parts >= hours.open && parts < hours.close
      : parts >= hours.open || parts < hours.close)
  );
}
