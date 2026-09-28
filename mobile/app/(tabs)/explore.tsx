import { useEffect } from "react";
import { FlatList } from "react-native";
import { useLocalSearchParams } from "expo-router";
import {
  Copy,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  Screen,
  ScreenHeader,
} from "../../components/common";
import { LocationCard } from "../../components/location";
import { DiscoveryFilters } from "../../components/location/DiscoveryFilters";
import { useDiscovery } from "../../store/DiscoveryProvider";
import { useDeviceLocation } from "../../store/LocationProvider";
export default function Explore() {
  const { q } = useLocalSearchParams<{ q?: string }>();
  const { data, loading, error, retry, setFilters } = useDiscovery();
  const { coordinates } = useDeviceLocation();
  useEffect(() => {
    if (q !== undefined) setFilters((current) => ({ ...current, query: q }));
  }, [q, setFilters]);
  return (
    <Screen scroll={false}>
      <ScreenHeader
        title="Find your focus."
        subtitle="A space for every kind of study session."
      />
      <DiscoveryFilters />
      <Copy muted>{data?.length ?? 0} study spaces · Seed data</Copy>
      <Copy muted>
        {coordinates
          ? "Distances are straight-line; radius results are capped at 100."
          : "Campus browsing · Enable location on Home for proximity sorting."}
      </Copy>
      {loading ? (
        <LoadingSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <FlatList
          data={data ?? []}
          keyExtractor={(l) => l.id}
          renderItem={({ item }) => <LocationCard location={item} />}
          ListEmptyComponent={
            <EmptyState
              title="Let’s widen the search"
              message="Try a different building or remove a filter."
            />
          }
        />
      )}
    </Screen>
  );
}
