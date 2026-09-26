import { useState } from "react";
import { View } from "react-native";
import { CampusMap } from "../../components/navigation/CampusMap";
import {
  Chip,
  Copy,
  DemoNote,
  EmptyState,
  ErrorState,
  IconButton,
  LoadingSkeleton,
  Screen,
  ScreenHeader,
  styles,
} from "../../components/common";
import { CompactLocationCard } from "../../components/location";
import { useAsync } from "../../hooks/useAsync";
import { locationService } from "../../services/locationService";
import { OccupancyLevel } from "../../types";
import { getOccupancyLevel, occupancyLabels } from "../../utils/occupancy";
import { spacing as s } from "../../theme";
export default function MapScreen() {
  const { data, loading, error, retry } = useAsync(
    locationService.getLocations,
  );
  const [filter, setFilter] = useState<OccupancyLevel | "any">("any");
  const [selected, setSelected] = useState<string | null>("zone-1");
  const [position, setPosition] = useState(true);
  const locations = (data ?? []).filter(
    (l) => filter === "any" || getOccupancyLevel(l.currentOccupancy) === filter,
  );
  const active = locations.find((l) => l.id === selected);
  return (
    <Screen>
      <ScreenHeader
        title="A new perspective."
        subtitle="Find your corner of campus."
      />
      <View style={[styles.wrap, { marginBottom: s.lg }]}>
        {(["any", "available", "moderate", "busy", "full"] as const).map(
          (x) => (
            <Chip
              key={x}
              label={x === "any" ? "All spaces" : occupancyLabels[x]}
              selected={filter === x}
              onPress={() => {
                setFilter(x);
                setSelected(null);
              }}
            />
          ),
        )}
      </View>
      {loading ? (
        <LoadingSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <>
          <CampusMap
            locations={locations}
            selectedId={selected}
            onSelect={setSelected}
            showPosition={position}
          />
          <View
            style={[
              styles.row,
              { justifyContent: "space-between", marginVertical: s.lg },
            ]}
          >
            <Copy variant="caption" muted>
              Tap an occupancy marker
            </Copy>
            <View style={styles.row}>
              <IconButton
                icon="locate-outline"
                label="Toggle demo starting point"
                active={position}
                onPress={() => setPosition(!position)}
              />
              <IconButton
                icon="refresh-outline"
                label="Recenter map and show all spaces"
                onPress={() => {
                  setFilter("any");
                  setSelected("zone-1");
                  setPosition(true);
                }}
              />
            </View>
          </View>
          {active ? (
            <CompactLocationCard location={active} />
          ) : (
            <EmptyState
              title="Pick a place to explore"
              message="Select a marker to see its floor, crowd level, and walking distance."
              icon="map-outline"
            />
          )}
        </>
      )}
      <DemoNote text="Illustrated campus map · schematic positions and demo starting point. No device location is used." />
    </Screen>
  );
}
