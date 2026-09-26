import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useState, useCallback } from "react";
import { FlatList, View } from "react-native";
import { useLocalSearchParams } from "expo-router";
import {
  Chip,
  Button,
  Copy,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  Screen,
  ScreenHeader,
  SearchBar,
  styles,
} from "../../components/common";
import { LocationCard } from "../../components/location";
import { FilterKind, FilterSheet } from "../../components/location/FilterSheet";
import { locationService } from "../../services/locationService";
import { useAsync } from "../../hooks/useAsync";
import { defaultFilters } from "../../utils/filters";
import { spacing as s } from "../../theme";
export default function Explore() {
  const { q } = useLocalSearchParams<{ q?: string }>();
  return <ExploreContent key={q ?? ""} query={q ?? ""} />;
}
function ExploreContent({ query }: { query: string }) {
  const [filters, setFilters] = useState({ ...defaultFilters, query });
  const [kind, setKind] = useState<FilterKind | null>(null);
  const debounced = useDebouncedValue(filters);
  const [page, setPage] = useState(1);
  const loader = useCallback(
    () => locationService.getLocationPage(debounced, page),
    [debounced, page],
  );
  const { data, loading, error, retry } = useAsync(loader);
  const locations = data?.items ?? [];
  const updateFilters = (next: typeof filters) => {
    setPage(1);
    setFilters(next);
  };
  return (
    <Screen scroll={false}>
      <ScreenHeader
        title="Find your focus."
        subtitle="A space for every kind of study session."
      />
      <SearchBar
        value={filters.query}
        onChangeText={(query) => updateFilters({ ...filters, query })}
        placeholder="Search buildings, rooms, or amenities"
      />
      <View style={[styles.wrap, { marginVertical: s.lg }]}>
        {(["Crowding", "Noise", "Amenities"] as const).map((k) => (
          <Chip
            key={k}
            label={`${k} ⌄`}
            selected={
              k === "Crowding"
                ? filters.crowding !== "any"
                : k === "Noise"
                  ? filters.noise !== "any"
                  : filters.amenities.length > 0
            }
            onPress={() => setKind(k)}
          />
        ))}
      </View>
      <View
        style={[
          styles.row,
          { justifyContent: "space-between", marginBottom: s.md },
        ]}
      >
        <Copy muted variant="caption">
          {loading
            ? "Loading…"
            : `${data?.total ?? 0} study spaces · Seed data`}
        </Copy>
        <Chip label="Reset" onPress={() => updateFilters(defaultFilters)} />
      </View>
      {loading ? (
        <LoadingSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <FlatList
          data={locations}
          keyExtractor={(l) => l.id}
          renderItem={({ item }) => <LocationCard location={item} />}
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={{ paddingBottom: s.xl }}
          ListFooterComponent={
            data && data.total > data.page_size ? (
              <View style={{ gap: s.md }}>
                <Copy muted>
                  Page {page} of {Math.ceil(data.total / data.page_size)}
                </Copy>
                {page > 1 && (
                  <Button
                    label="Previous page"
                    secondary
                    onPress={() => setPage(page - 1)}
                  />
                )}{" "}
                {page * data.page_size < data.total && (
                  <Button
                    label="Next page"
                    secondary
                    onPress={() => setPage(page + 1)}
                  />
                )}
              </View>
            ) : null
          }
          ListEmptyComponent={
            <EmptyState
              title="Let’s widen the search"
              message="Try a different building or remove a filter to find more spaces."
              action="Clear filters"
              onAction={() => updateFilters(defaultFilters)}
            />
          }
        />
      )}
      <FilterSheet
        kind={kind}
        onClose={() => setKind(null)}
        value={filters}
        onChange={updateFilters}
      />
    </Screen>
  );
}
