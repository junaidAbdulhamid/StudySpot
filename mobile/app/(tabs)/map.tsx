import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { View } from "react-native";
import { CampusMap } from "../../components/navigation/CampusMap";
import { mapGroups } from "../../components/navigation/mapModel";
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
import { LocationCard } from "../../components/location";
import { DiscoveryFilters } from "../../components/location/DiscoveryFilters";
import { LocationPermission } from "../../components/location/LocationPermission";
import { useDiscovery } from "../../store/DiscoveryProvider";
import { useDeviceLocation } from "../../store/LocationProvider";
import { useAsync } from "../../hooks/useAsync";
import { campusService } from "../../services/campusService";
export default function MapScreen() {
  const { data, loading, error, retry, filters } = useDiscovery();
  useFocusEffect(
    useCallback(() => {
      retry();
      const timer = setInterval(retry, 60000);
      return () => clearInterval(timer);
    }, [retry]),
  );
  const campus = useAsync(campusService.getCampuses);
  const device = useDeviceLocation();
  const [selected, setSelected] = useState<string | null>(null);
  const [recenter, setRecenter] = useState(0);
  const locations = data ?? [];
  const active = locations.find((l) => l.id === selected);
  const groups = mapGroups(locations);
  const center =
    device.coordinates ??
    campus.data?.find((c) => c.id === filters.campusId) ??
    campus.data?.[0];
  return (
    <Screen>
      <ScreenHeader
        title="A new perspective."
        subtitle="Find your corner of campus."
      />
      <DiscoveryFilters />
      {loading ? (
        <LoadingSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <>
          {campus.error && (
            <ErrorState message={campus.error} onRetry={campus.retry} />
          )}
          <CampusMap
            locations={locations}
            selectedId={selected}
            onSelect={setSelected}
            center={center}
            position={device.coordinates}
            recenter={recenter}
          />
          <IconButton
            icon="locate-outline"
            label="Recenter map"
            onPress={() => {
              void device.refreshLocation();
              setRecenter((value) => value + 1);
            }}
          />
          <Copy muted>
            Select a building, then choose a study zone. Crowd levels are
            estimates from recent reports.
          </Copy>
          <View style={styles.wrap}>
            {groups.map((group) => (
              <Chip
                key={group.id}
                label={group.best.building}
                selected={group.locations.some((l) => l.id === selected)}
                onPress={() => setSelected(group.best.id)}
              />
            ))}
          </View>
          {active && (
            <>
              <View style={styles.wrap}>
                {locations
                  .filter((l) => l.buildingId === active.buildingId)
                  .map((l) => (
                    <Chip
                      key={l.id}
                      label={l.floor}
                      selected={l.id === selected}
                      onPress={() => setSelected(l.id)}
                    />
                  ))}
              </View>
              <LocationCard location={active} />
            </>
          )}
          {!locations.length && (
            <EmptyState
              title="No matching spaces"
              message="Try a larger radius or reset your filters."
            />
          )}
        </>
      )}
      <LocationPermission />
      <DemoNote text="Crowd estimates may be unknown until students report. GPS cannot identify your indoor floor." />
    </Screen>
  );
}
