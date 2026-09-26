import { FlatList } from "react-native";
import { router } from "expo-router";
import {
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  Screen,
  ScreenHeader,
} from "../common";
import { LocationCard } from "./index";
import { useAsync } from "../../hooks/useAsync";
import { locationService } from "../../services/locationService";
import { useApp } from "../../store/AppStore";
export function SavedLocations({ recent = false }: { recent?: boolean }) {
  const { favorites, recent: history } = useApp();
  const { data, loading, error, retry } = useAsync(
    locationService.getLocations,
  );
  const ids = recent ? history : favorites;
  const locations = ids.flatMap((id) =>
    data?.find((l) => l.id === id) ? [data.find((l) => l.id === id)!] : [],
  );
  return (
    <Screen scroll={false}>
      <ScreenHeader
        title={recent ? "Your recent spaces." : "Your familiar favorites."}
        subtitle={
          recent
            ? "Pick up where you left off."
            : "Good places are worth keeping close."
        }
        back
      />
      {loading ? (
        <LoadingSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <FlatList
          data={locations}
          keyExtractor={(l) => l.id}
          renderItem={({ item }) => <LocationCard location={item} />}
          ListEmptyComponent={
            <EmptyState
              title={recent ? "A fresh start." : "No favorites yet."}
              message={
                recent
                  ? "The spaces you explore will appear here."
                  : "Save your go-to study spots to see them here."
              }
              icon={recent ? "time-outline" : "heart-outline"}
              action="Explore spaces"
              onAction={() => router.push("/(tabs)/explore")}
            />
          }
        />
      )}
    </Screen>
  );
}
