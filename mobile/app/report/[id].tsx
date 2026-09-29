import { useCallback, useState } from "react";
import { View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import {
  Button,
  Card,
  Chip,
  Copy,
  Icon,
  Screen,
  ScreenHeader,
  styles,
} from "../../components/common";
import { LocationImage } from "../../components/location";
import { LocationBoundary } from "../../components/location/LocationBoundary";
import { useLocation } from "../../hooks/useLocation";
import { useAsync } from "../../hooks/useAsync";
import { useDeviceLocation } from "../../store/LocationProvider";
import { errorMessage } from "../../services/api/client";
import { CrowdLevel, occupancyService } from "../../services/occupancyService";
import { colors as c, spacing as s, radius as r } from "../../theme";
import { getOccupancyColor } from "../../utils/occupancy";
export default function Report() {
  const state = useLocation();
  const { mode } = useLocalSearchParams<{ mode?: string }>();
  const [tab, setTab] = useState(
    mode === "crowd" ? "Report Crowd" : "Check In",
  );
  const [level, setLevel] = useState<CrowdLevel | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { coordinates } = useDeviceLocation();
  const active = useAsync(
    useCallback(() => occupancyService.activeCheckIn(), []),
  );
  async function handleCheckIn(locationId: string) {
    setBusy(true);
    setError(null);
    try {
      if (active.data?.location_id === locationId)
        await occupancyService.checkOut(active.data.id);
      else await occupancyService.checkIn(locationId, coordinates);
      active.retry();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }
  async function handleReport(locationId: string) {
    if (!level) return;
    setBusy(true);
    setError(null);
    try {
      await occupancyService.submitReport(locationId, level, coordinates);
      setSubmitted(true);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <LocationBoundary state={state}>
      {(l) => (
        <Screen>
          <ScreenHeader title="A little help goes a long way." back />
          <View
            style={{
              borderRadius: r.lg,
              overflow: "hidden",
              marginBottom: s.xl,
            }}
          >
            <LocationImage location={l} height={160}>
              <View />
              <View>
                <Copy variant="heading">{l.name}</Copy>
                <Copy muted>{l.floor}</Copy>
              </View>
            </LocationImage>
          </View>
          <View style={[styles.row, { marginBottom: s.xl }]}>
            {["Check In", "Report Crowd"].map((x) => (
              <Chip
                key={x}
                label={x}
                selected={tab === x}
                onPress={() => setTab(x)}
              />
            ))}
          </View>
          {tab === "Check In" ? (
            <Card style={{ alignItems: "center", padding: s.xl }}>
              <Icon
                name={
                  active.data?.location_id === l.id
                    ? "checkmark-circle-outline"
                    : "location-outline"
                }
                size={70}
                color={c.primary}
              />
              <Copy variant="title">
                {active.data?.location_id === l.id
                  ? "Checked in"
                  : "Study here?"}
              </Copy>
              <Copy muted style={{ textAlign: "center" }}>
                {active.data?.location_id === l.id
                  ? "Thanks for helping StudySpot. Enjoy your focus time."
                  : "Check in to help improve crowd estimates. Other students see only aggregate information."}
              </Copy>
              {active.data && active.data.location_id !== l.id && (
                <Copy muted variant="caption">
                  This will end your previous check-in.
                </Copy>
              )}
              <Button
                label={
                  active.data?.location_id === l.id ? "Check Out" : "Check In"
                }
                disabled={busy || active.loading}
                onPress={() => void handleCheckIn(l.id)}
              />
            </Card>
          ) : submitted ? (
            <Card style={{ alignItems: "center", padding: s.xl }}>
              <Icon name="checkmark-circle" size={64} color={c.primary} />
              <Copy variant="title">You made a difference.</Copy>
              <Copy muted style={{ textAlign: "center" }}>
                Your report helps other students choose a study spot.
              </Copy>
              <Button
                label="Back to location"
                onPress={() => router.replace(`/location/${l.id}`)}
              />
              <Button
                label="Submit another report"
                secondary
                onPress={() => {
                  setSubmitted(false);
                  setLevel(null);
                }}
              />
            </Card>
          ) : (
            <View style={{ gap: s.lg }}>
              <Copy variant="heading">How crowded is it right now?</Copy>
              {(
                ["lots_of_seats", "moderate", "busy", "nearly_full"] as const
              ).map((x, i) => (
                <View
                  key={x}
                  style={{
                    borderLeftWidth: 3,
                    borderLeftColor: getOccupancyColor(
                      ["available", "moderate", "busy", "full"][i] as
                        "available" | "moderate" | "busy" | "full",
                    ),
                    paddingLeft: s.md,
                  }}
                >
                  <Chip
                    label={
                      ["Lots of seats", "Moderate", "Busy", "Nearly full"][i]!
                    }
                    icon="people-outline"
                    selected={level === x}
                    onPress={() => setLevel(x)}
                  />
                </View>
              ))}
              <Button
                label="Submit Crowd Report"
                disabled={!level || busy}
                onPress={() => void handleReport(l.id)}
              />
            </View>
          )}
          {error && <Copy color={c.danger}>{error}</Copy>}
          {active.error && (
            <Copy muted variant="caption">
              {active.error}
            </Copy>
          )}
          <Copy muted variant="caption">
            Location, when available, helps check proximity. GPS cannot verify
            an indoor floor.
          </Copy>
          <Button
            label="Return Home"
            secondary
            onPress={() => router.replace("/(tabs)")}
          />
        </Screen>
      )}
    </LocationBoundary>
  );
}
