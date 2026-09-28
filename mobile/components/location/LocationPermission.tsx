import { Button, Card, Copy } from "../common";
import { useDeviceLocation } from "../../store/LocationProvider";
export function LocationPermission() {
  const location = useDeviceLocation();
  if (location.coordinates)
    return location.error ? <Copy muted>{location.error}</Copy> : null;
  if (location.dismissed && !location.error)
    return (
      <Button
        secondary
        label={
          location.isLoading
            ? "Finding location…"
            : "Enable location for nearby spaces"
        }
        disabled={location.isLoading}
        onPress={() => void location.requestPermission()}
      />
    );
  return (
    <Card>
      <Copy variant="heading">Find the best study spots near you</Copy>
      <Copy muted>
        {location.error ??
          "StudySpot uses your location while you’re using the app to show nearby study spaces and calculate distance. Your coordinates are not saved to your account."}
      </Copy>
      <Button
        label={location.isLoading ? "Finding location…" : "Enable Location"}
        disabled={location.isLoading}
        onPress={() => void location.requestPermission()}
      />
      {!location.dismissed && (
        <Button label="Not Now" secondary onPress={location.dismiss} />
      )}
    </Card>
  );
}
