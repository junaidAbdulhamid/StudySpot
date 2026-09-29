import { useState, useCallback } from "react";
import { router, useFocusEffect } from "expo-router";
import { useDeviceLocation } from "../../store/LocationProvider";
import { LocationPermission } from "../../components/location/LocationPermission";
import { Pressable, View } from "react-native";
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
import { occupancyService } from "../../services/occupancyService";
import { errorMessage } from "../../services/api/client";
import { useApp } from "../../store/AppStore";
import { colors as c, spacing as s } from "../../theme";
import { rankLocations } from "../../utils/recommendations";
export default function Home() {
  const { coordinates } = useDeviceLocation();
  const { data, loading, error, retry } = useAsync(
    useCallback(
      () =>
        coordinates
          ? locationService.getNearbyLocations(
              coordinates.latitude,
              coordinates.longitude,
            )
          : locationService.getLocations(),
      [coordinates],
    ),
  );
  const active = useAsync(
    useCallback(() => occupancyService.activeCheckIn(), []),
  );
  const activeRetry = active.retry;
  useFocusEffect(
    useCallback(() => {
      retry();
    }, [retry]),
  );
  useFocusEffect(
    useCallback(() => {
      activeRetry();
    }, [activeRetry]),
  );
  const { preferences, favorites, user } = useApp();
  const matches = coordinates
    ? (data ?? []).map((location) => ({ location }))
    : rankLocations(data ?? [], preferences);
  const activeLocation = data?.find(
    (item) => item.id === active.data?.location_id,
  );
  const [query, setQuery] = useState("");
  const [checkoutError, setCheckoutError] = useState("");
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
      {active.data && (
        <Card style={{ marginBottom: s.lg }}>
          <Copy variant="label" color={c.primary}>
            CURRENTLY STUDYING
          </Copy>
          <Copy>
            {activeLocation
              ? `${activeLocation.name} · ${activeLocation.floor}`
              : "Study space"}
          </Copy>
          <Copy muted variant="caption">
            Checked in{" "}
            {new Date(active.data.checked_in_at).toLocaleTimeString([], {
              hour: "numeric",
              minute: "2-digit",
            })}
          </Copy>
          <Button
            label="Check Out"
            secondary
            onPress={() => {
              if (active.data)
                void occupancyService
                  .checkOut(active.data.id)
                  .then(() => {
                    setCheckoutError("");
                    active.retry();
                    retry();
                  })
                  .catch((cause) => setCheckoutError(errorMessage(cause)));
            }}
          />
          {checkoutError && (
            <Copy muted variant="caption">
              {checkoutError}
            </Copy>
          )}
        </Card>
      )}
      <View style={[styles.row, { marginBottom: s.xl }]}>
        <Icon name="location-outline" size={16} color={c.primary} />
        <Copy variant="caption" muted>
          {data?.[0]?.campusName ?? "Campus study spaces"}
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
      <LocationPermission />
      <SectionHeader
        title={coordinates ? "Study spots near you" : "Best spots for you"}
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
      <DemoNote text="Crowd levels are estimates from recent contributions; forecasts remain illustrative." />
    </Screen>
  );
}
