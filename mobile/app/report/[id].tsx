import { useState } from "react";
import { View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import {
  Button,
  Card,
  Chip,
  Copy,
  DemoNote,
  Icon,
  Screen,
  ScreenHeader,
  styles,
} from "../../components/common";
import { LocationImage } from "../../components/location";
import { LocationBoundary } from "../../components/location/LocationBoundary";
import { useLocation } from "../../hooks/useLocation";
import { useApp } from "../../store/AppStore";
import { OccupancyLevel } from "../../types";
import { colors as c, spacing as s, radius as r } from "../../theme";
import { getOccupancyColor } from "../../utils/occupancy";
export default function Report() {
  const state = useLocation();
  const { mode } = useLocalSearchParams<{ mode?: string }>();
  const [tab, setTab] = useState(
    mode === "crowd" ? "Report Crowd" : "Check In",
  );
  const [level, setLevel] = useState<OccupancyLevel | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const { checkIn, setCheckIn, addReport } = useApp();
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
                  checkIn === l.id
                    ? "checkmark-circle-outline"
                    : "location-outline"
                }
                size={70}
                color={c.primary}
              />
              <Copy variant="title">
                {checkIn === l.id ? "Checked in" : "You’re here!"}
              </Copy>
              <Copy muted style={{ textAlign: "center" }}>
                {checkIn === l.id
                  ? "Thanks for helping StudySpot. Enjoy your focus time."
                  : "Check in to help improve crowd estimates."}
              </Copy>
              {checkIn && checkIn !== l.id && (
                <Copy muted variant="caption">
                  This will move your demo check-in from your previous space.
                </Copy>
              )}
              <Button
                label={checkIn === l.id ? "Check Out" : "Check In"}
                onPress={() => setCheckIn(checkIn === l.id ? null : l.id)}
              />
            </Card>
          ) : submitted ? (
            <Card style={{ alignItems: "center", padding: s.xl }}>
              <Icon name="checkmark-circle" size={64} color={c.primary} />
              <Copy variant="title">You made a difference.</Copy>
              <Copy muted style={{ textAlign: "center" }}>
                Your demo report is saved for this session. Thanks for looking
                out for your campus.
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
              {(["available", "moderate", "busy", "full"] as const).map(
                (x, i) => (
                  <View
                    key={x}
                    style={{
                      borderLeftWidth: 3,
                      borderLeftColor: getOccupancyColor(x),
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
                ),
              )}
              <Button
                label="Submit Crowd Report"
                disabled={!level}
                onPress={() => {
                  if (level) {
                    addReport({
                      locationId: l.id,
                      level,
                      createdAt: new Date().toISOString(),
                    });
                    setSubmitted(true);
                  }
                }}
              />
            </View>
          )}
          <DemoNote text="Demo only · no location verification or report is sent to a server." />
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
