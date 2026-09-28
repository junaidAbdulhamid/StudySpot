import { Linking, Platform } from "react-native";
import { Coordinate } from "../../utils/geospatial";
export async function openDirections(destination: Coordinate) {
  const point = `${destination.latitude},${destination.longitude}`;
  const fallback = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(point)}&travelmode=walking`;
  const preferred =
    Platform.OS === "ios"
      ? `https://maps.apple.com/?daddr=${encodeURIComponent(point)}&dirflg=w`
      : fallback;
  try {
    await Linking.openURL(preferred);
  } catch {
    await Linking.openURL(fallback);
  }
}
