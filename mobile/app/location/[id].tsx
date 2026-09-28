import { useEffect } from "react";
import { View } from "react-native";
import { router } from "expo-router";
import {
  Button,
  Card,
  Copy,
  DemoNote,
  IconButton,
  Screen,
  SectionHeader,
  styles,
} from "../../components/common";
import {
  AmenityBadge,
  DistanceBadge,
  FavoriteButton,
  LocationImage,
  NoiseBadge,
} from "../../components/location";
import {
  OccupancyBadge,
  OccupancyBar,
  StatCard,
} from "../../components/occupancy";
import { LocationBoundary } from "../../components/location/LocationBoundary";
import { WalkingRouteSummary } from "../../components/location/WalkingRouteSummary";
import { useLocation } from "../../hooks/useLocation";
import { useApp } from "../../store/AppStore";
import { colors as c, radius as r, spacing as s } from "../../theme";
import {
  formatOperatingHours,
  getOccupancyLevel,
  formatOccupancy,
} from "../../utils/occupancy";
import { isLocationOpen } from "../../utils/geospatial";
export default function Details() {
  const state = useLocation();
  const { visit } = useApp();
  const id = state.data?.id;
  useEffect(() => {
    if (id) visit(id);
  }, [id, visit]);
  return (
    <LocationBoundary state={state}>
      {(l) => (
        <Screen>
          <View style={{ borderRadius: r.lg, overflow: "hidden" }}>
            <LocationImage location={l} height={290}>
              <View
                style={[
                  styles.row,
                  { justifyContent: "space-between", flexWrap: "wrap" },
                ]}
              >
                <IconButton
                  icon="arrow-back"
                  label="Go back"
                  onPress={() =>
                    router.canGoBack()
                      ? router.back()
                      : router.replace("/(tabs)")
                  }
                />
                <FavoriteButton id={l.id} />
              </View>
              <View>
                <Copy variant="label" color={c.primary}>
                  {l.floor.toUpperCase()}
                </Copy>
                <Copy variant="title">{l.name}</Copy>
              </View>
            </LocationImage>
          </View>
          <DemoNote />
          <Card>
            <Copy variant="label" muted>
              CURRENT OCCUPANCY
            </Copy>
            <View
              style={[
                styles.row,
                { justifyContent: "space-between", flexWrap: "wrap" },
              ]}
            >
              <Copy variant="hero">{formatOccupancy(l.currentOccupancy)}</Copy>
              <OccupancyBadge percent={l.currentOccupancy} />
            </View>
            <OccupancyBar percent={l.currentOccupancy} />
            <Copy muted>
              {
                {
                  available:
                    "Lots of seats available. Make yourself comfortable.",
                  moderate: "A few good seats are waiting for you.",
                  busy: "Filling up. Consider a quieter alternative.",
                  full: "Nearly full. Explore nearby spaces.",
                  unknown: "No occupancy estimate is available yet.",
                }[getOccupancyLevel(l.currentOccupancy)]
              }
            </Copy>
          </Card>
          <View style={[styles.wrap, { marginTop: s.lg }]}>
            <NoiseBadge noise={l.noiseLevel} />
            <DistanceBadge
              minutes={l.walkingMinutes}
              meters={l.distanceMeters}
            />
            {l.amenities.map((a) => (
              <AmenityBadge key={a} amenity={a} />
            ))}
          </View>
          <WalkingRouteSummary key={l.id} destination={l} />
          <SectionHeader title="A little about this space" />
          <Copy muted>{l.description}</Copy>
          <View style={[styles.row, { marginVertical: s.xl }]}>
            <StatCard
              label="Demo opening hours"
              value={formatOperatingHours(l.hours)}
            />
            {l.timezone && (
              <StatCard
                label="Right now"
                value={isLocationOpen(l.hours, l.timezone) ? "Open" : "Closed"}
              />
            )}
          </View>
          <View style={{ gap: s.md }}>
            <Button
              label="Check In"
              icon="location-outline"
              onPress={() =>
                router.push({
                  pathname: "/report/[id]",
                  params: { id: l.id, mode: "checkin" },
                })
              }
            />
            <Button
              label="Report Crowd"
              icon="people-outline"
              secondary
              onPress={() =>
                router.push({
                  pathname: "/report/[id]",
                  params: { id: l.id, mode: "crowd" },
                })
              }
            />
            <Button
              label="View Predictions"
              icon="stats-chart-outline"
              secondary
              onPress={() => router.push(`/predictions/${l.id}`)}
            />
            <Button
              label="Directions"
              icon="navigate-outline"
              secondary
              onPress={() => router.push(`/directions/${l.id}`)}
            />
          </View>
          <DemoNote text="Photos illustrate the study-space atmosphere; they are not verified GMU location photos." />
        </Screen>
      )}
    </LocationBoundary>
  );
}
