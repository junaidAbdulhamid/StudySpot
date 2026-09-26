import { useState } from "react";
import { Pressable, View } from "react-native";
import { router } from "expo-router";
import {
  Avatar,
  Button,
  Card,
  Copy,
  DemoNote,
  ErrorState,
  EmptyState,
  Icon,
  IconName,
  LoadingSkeleton,
  Screen,
  SearchBar,
  SectionHeader,
  styles,
} from "../../components/common";
import { CompactLocationCard, LocationCard } from "../../components/location";
import { useAsync } from "../../hooks/useAsync";
import { locationService } from "../../services/locationService";
import { useApp } from "../../store/AppStore";
import { colors as c, spacing as s } from "../../theme";
import { rankLocations } from "../../utils/recommendations";
export default function Home() {
  const { data, loading, error, retry } = useAsync(
    locationService.getLocations,
  );
  const { preferences, favorites, user } = useApp();
  const matches = rankLocations(data ?? [], preferences);
  const [query, setQuery] = useState("");
  const hour = new Date().getHours();
  const greeting =
    hour < 12
      ? "Good morning,"
      : hour < 17
        ? "Good afternoon,"
        : "Good evening,";
  return (
    <Screen>
      <View
        style={[
          styles.row,
          { justifyContent: "space-between", marginBottom: s.xl },
        ]}
      >
        <View>
          <Copy muted>{greeting}</Copy>
          <Copy variant="title">
            {user.name.split(" ")[0]}{" "}
            <Copy color={c.primary} variant="title">
              ✦
            </Copy>
          </Copy>
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Open profile"
          onPress={() => router.push("/(tabs)/profile")}
        >
          <Avatar name={user.name} />
        </Pressable>
      </View>
      <View style={[styles.row, { marginBottom: s.xl }]}>
        <Icon name="location-outline" size={16} color={c.primary} />
        <Copy variant="caption" muted>
          GEORGE MASON · FAIRFAX CAMPUS
        </Copy>
      </View>
      <SearchBar
        value={query}
        onChangeText={setQuery}
        onSubmit={() =>
          router.push({ pathname: "/(tabs)/explore", params: { q: query } })
        }
      />
      <View
        style={[
          styles.row,
          { justifyContent: "space-between", marginTop: s.xl },
        ]}
      >
        {(
          [
            {
              label: "Find a spot",
              icon: "sparkles-outline",
              href: "/find-spot",
            },
            { label: "Map", icon: "map-outline", href: "/(tabs)/map" },
            { label: "Favorites", icon: "heart-outline", href: "/favorites" },
            { label: "Recent", icon: "time-outline", href: "/recent" },
          ] as const
        ).map((a) => (
          <Pressable
            key={a.label}
            accessibilityRole="button"
            onPress={() => router.push(a.href)}
            style={{ alignItems: "center", gap: s.sm, flex: 1, minHeight: 76 }}
          >
            <View style={[styles.iconButton, { width: 50, height: 50 }]}>
              <Icon name={a.icon as IconName} color={c.primary} />
            </View>
            <Copy variant="caption" muted>
              {a.label}
            </Copy>
          </Pressable>
        ))}
      </View>
      <Card style={{ marginTop: s.xl, padding: s.xl }}>
        <View style={styles.row}>
          <Icon name="sparkles-outline" color={c.primary} />
          <Copy variant="label" color={c.primary}>
            LESS WANDERING, MORE FOCUS
          </Copy>
        </View>
        <Copy variant="title">Your next great idea needs a good spot.</Copy>
        <Copy muted>Tell us your vibe. We’ll find your space.</Copy>
        <Button
          label="Find Me a Spot"
          icon="arrow-forward"
          onPress={() => router.push("/find-spot")}
        />
      </Card>
      <SectionHeader
        title="Best spots for you"
        action="See all"
        onPress={() => router.push("/(tabs)/explore")}
      />
      {loading ? (
        <LoadingSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <>
          {matches.slice(0, 2).map((x) => (
            <LocationCard key={x.location.id} location={x.location} />
          ))}
          {matches.length === 0 && (
            <EmptyState
              title="A little more room to explore"
              message="No spaces meet all your preferences. Adjust your session to see more matches."
              action="Adjust preferences"
              onAction={() => router.push("/find-spot")}
            />
          )}
          <SectionHeader title="Trending study spots" />
          {data
            ?.filter((l) => ["zone-6", "zone-9", "zone-11"].includes(l.id))
            .map((l) => (
              <CompactLocationCard key={l.id} location={l} />
            ))}
          <SectionHeader
            title="Your favorites"
            action="View all"
            onPress={() => router.push("/favorites")}
          />
          {data
            ?.filter((l) => favorites.includes(l.id))
            .slice(0, 2)
            .map((l) => (
              <CompactLocationCard key={l.id} location={l} />
            ))}
          {favorites.length === 0 && (
            <Copy muted>Tap a heart to keep your favorite spaces close.</Copy>
          )}
        </>
      )}
      <DemoNote />
    </Screen>
  );
}
