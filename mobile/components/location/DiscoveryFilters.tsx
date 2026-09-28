import { useState } from "react";
import { View } from "react-native";
import { Chip, SearchBar, styles } from "../common";
import { FilterKind, FilterSheet } from "./FilterSheet";
import { useDiscoveryFilters } from "../../store/DiscoveryProvider";
import { useDeviceLocation } from "../../store/LocationProvider";
import { defaultFilters } from "../../utils/filters";
export function DiscoveryFilters() {
  const { filters, setFilters } = useDiscoveryFilters();
  const { coordinates } = useDeviceLocation();
  const [kind, setKind] = useState<FilterKind | null>(null);
  return (
    <View style={{ gap: 12, marginVertical: 16 }}>
      <SearchBar
        value={filters.query}
        onChangeText={(query) => setFilters({ ...filters, query })}
        placeholder="Search buildings, rooms, or amenities"
      />
      <View style={styles.wrap}>
        {(["Crowding", "Noise", "Amenities"] as const).map((value) => (
          <Chip
            key={value}
            label={`${value} ⌄`}
            onPress={() => setKind(value)}
            selected={
              value === "Crowding"
                ? filters.crowding !== "any"
                : value === "Noise"
                  ? filters.noise !== "any"
                  : filters.amenities.length > 0
            }
          />
        ))}
        <Chip
          label="Open now"
          selected={filters.openNow}
          onPress={() => setFilters({ ...filters, openNow: !filters.openNow })}
        />
        {coordinates && (
          <>
            <Chip
              label="Nearest"
              selected={filters.nearest}
              onPress={() =>
                setFilters({ ...filters, nearest: !filters.nearest })
              }
            />
            {[500, 1500, 3000].map((radius) => (
              <Chip
                key={radius}
                label={`${radius} m radius`}
                selected={(filters.radiusMeters ?? 1500) === radius}
                onPress={() => setFilters({ ...filters, radiusMeters: radius })}
              />
            ))}
          </>
        )}
        <Chip label="Reset" onPress={() => setFilters(defaultFilters)} />
      </View>
      <FilterSheet
        key={kind ?? "closed"}
        kind={kind}
        value={filters}
        onChange={setFilters}
        onClose={() => setKind(null)}
      />
    </View>
  );
}
