import { useAsync } from "../../hooks/useAsync";
import { locationService } from "../../services/locationService";
import { useState, useCallback } from "react";
import { View } from "react-native";
import {
  Button,
  Card,
  Chip,
  Copy,
  DemoNote,
  Icon,
  Screen,
  ScreenHeader,
  SectionHeader,
  styles,
} from "../../components/common";
import { BarChart, OccupancyMeter, StatCard } from "../../components/occupancy";
import { LocationBoundary } from "../../components/location/LocationBoundary";
import { useLocation } from "../../hooks/useLocation";
import { colors as c, spacing as s } from "../../theme";
import { router, useLocalSearchParams } from "expo-router";
import { getOccupancyLevel, formatEstimateAge } from "../../utils/occupancy";
export default function Predictions() {
  const locationState = useLocation();
  const { id } = useLocalSearchParams<{ id: string }>();
  const forecasts = useAsync(
    useCallback(() => locationService.getPredictions(id), [id]),
  );
  const state = {
    ...locationState,
    data: locationState.data
      ? { ...locationState.data, predictions: forecasts.data ?? [] }
      : undefined,
    loading: locationState.loading || forecasts.loading,
    error: locationState.error ?? forecasts.error,
    retry: () => {
      locationState.retry();
      forecasts.retry();
    },
  };
  const [tab, setTab] = useState("Predictions");
  return (
    <LocationBoundary state={state}>
      {(l) => {
        const busy = l.predictions.find(
          (p) =>
            p.hoursAhead > 0 &&
            ["busy", "full"].includes(getOccupancyLevel(p.percent)),
        );
        return (
          <Screen>
            <ScreenHeader
              title={l.name}
              subtitle={`${l.floor} · Occupancy outlook`}
              back
            />
            <View style={[styles.row, { marginBottom: s.xl }]}>
              {["Live", "Predictions"].map((x) => (
                <Chip
                  key={x}
                  label={x}
                  selected={tab === x}
                  onPress={() => setTab(x)}
                />
              ))}
            </View>
            {tab === "Live" ? (
              <>
                <Card>
                  <Copy variant="label" muted>
                    CURRENT OCCUPANCY
                  </Copy>
                  <OccupancyMeter percent={l.currentOccupancy} />
                  <Copy muted style={{ textAlign: "center" }}>
                    A snapshot of your study space.
                  </Copy>
                </Card>
                <View style={[styles.row, { marginTop: s.lg }]}>
                  <StatCard
                    label="Confidence"
                    value={l.occupancyConfidence ?? "Unavailable"}
                  />
                  <StatCard
                    label="Last updated"
                    value={formatEstimateAge(l.estimatedAt)}
                  />
                </View>
              </>
            ) : (
              <>
                <Card>
                  <View
                    style={[styles.row, { justifyContent: "space-between" }]}
                  >
                    <Copy variant="heading">Your next few hours</Copy>
                    <Icon name="trending-up" color={c.primary} />
                  </View>
                  <Copy muted>Plan a little ahead. Find your window.</Copy>
                  <BarChart
                    label="Mock occupancy forecast over four hours"
                    points={[
                      ...(l.currentOccupancy === null
                        ? []
                        : [{ label: "Now", percent: l.currentOccupancy }]),
                      ...l.predictions,
                    ]}
                  />
                </Card>
                <Card style={{ marginTop: s.lg }}>
                  <Icon name="sparkles-outline" color={c.primary} />
                  <Copy>
                    {busy
                      ? `Expected to be busy in ${Math.ceil(busy.hoursAhead)} ${Math.ceil(busy.hoursAhead) === 1 ? "hour" : "hours"}. Arrive earlier for more choice.`
                      : l.predictions.length
                        ? "The seeded forecast stays below busy levels."
                        : "No future forecast records are available. Seed forecasts expire; refresh the development seed to see new examples."}
                  </Copy>
                </Card>
              </>
            )}
            <SectionHeader title="Recent observations" />
            <Card>
              <Copy muted variant="caption">
                Persisted seed observations · times shown on your device
              </Copy>
              <BarChart
                label="Mock typical daily occupancy"
                points={l.historical.map((percent, i) => ({
                  percent,
                  label: l.historicalLabels?.[i] ?? String(i + 1),
                }))}
              />
            </Card>
            <DemoNote text="Estimates and forecasts are persisted seed records, not live occupancy or ML predictions. Update times come from the database." />
            <Button
              label="Check In / Report Crowd"
              secondary
              onPress={() => router.push(`/report/${l.id}`)}
            />
          </Screen>
        );
      }}
    </LocationBoundary>
  );
}
