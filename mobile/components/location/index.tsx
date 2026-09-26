import React from "react";
import { ImageBackground, Pressable, View } from "react-native";
import { router } from "expo-router";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  ReduceMotion,
} from "react-native-reanimated";
import { StudyLocation, Amenity } from "../../types";
import { colors as c, radius as r, spacing as s } from "../../theme";
import { Chip, Copy, Icon, styles } from "../common";
import { OccupancyBadge, OccupancyBar } from "../occupancy";
import { useApp } from "../../store/AppStore";
import { formatWalkingDistance } from "../../utils/occupancy";
const images = {
  library: require("../../assets/library.jpg"),
  hall: require("../../assets/hall.jpg"),
  commons: require("../../assets/commons.jpg"),
};
export function LocationImage({
  location,
  height = 170,
  children,
}: {
  location: StudyLocation;
  height?: number;
  children?: React.ReactNode;
}) {
  return (
    <ImageBackground
      source={
        location.imageUrl ? { uri: location.imageUrl } : images[location.image]
      }
      accessibilityLabel={`Illustrative ${location.image} study space`}
      style={{ height, backgroundColor: c.surfaceElevated }}
      imageStyle={{ opacity: 0.8 }}
    >
      <View
        style={{
          flex: 1,
          padding: s.lg,
          justifyContent: "space-between",
          flexWrap: "wrap",
          backgroundColor: c.scrim,
        }}
      >
        {children}
      </View>
    </ImageBackground>
  );
}
export function FavoriteButton({ id }: { id: string }) {
  const { favorites, toggleFavorite, pendingFavorites } = useApp();
  const selected = favorites.includes(id);
  const scale = useSharedValue(1);
  const animated = useAnimatedStyle(() => ({
    transform: [{ scale: scale.get() }],
  }));
  return (
    <Animated.View style={animated}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={
          selected ? "Remove from favorites" : "Save to favorites"
        }
        accessibilityState={{
          selected,
          disabled: pendingFavorites.includes(id),
        }}
        disabled={pendingFavorites.includes(id)}
        onPress={(e) => {
          e.stopPropagation();
          toggleFavorite(id);
          scale.set(0.8);
          scale.set(withSpring(1, { reduceMotion: ReduceMotion.System }));
        }}
        style={[styles.iconButton, { backgroundColor: c.background }]}
      >
        <Icon
          name={selected ? "heart" : "heart-outline"}
          color={selected ? c.primary : c.textPrimary}
        />
      </Pressable>
    </Animated.View>
  );
}
export function AmenityBadge({ amenity }: { amenity: Amenity }) {
  return (
    <Chip
      label={amenity}
      icon={
        amenity === "Outlets"
          ? "flash-outline"
          : amenity === "Natural light"
            ? "sunny-outline"
            : amenity === "Food nearby"
              ? "cafe-outline"
              : "grid-outline"
      }
    />
  );
}
export function DistanceBadge({ minutes }: { minutes: number | null }) {
  return <Chip label={formatWalkingDistance(minutes)} icon="walk-outline" />;
}
export function NoiseBadge({ noise }: { noise: StudyLocation["noiseLevel"] }) {
  return (
    <Chip
      label={noise.charAt(0).toUpperCase() + noise.slice(1)}
      icon={noise === "quiet" ? "volume-low-outline" : "chatbubbles-outline"}
    />
  );
}
export function LocationCard({
  location,
  compact = false,
}: {
  location: StudyLocation;
  compact?: boolean;
}) {
  const open = () => router.push(`/location/${location.id}`);
  if (compact)
    return (
      <View
        style={[
          styles.card,
          { flexDirection: "row", alignItems: "center", marginBottom: s.md },
        ]}
      >
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`View ${location.name}, ${location.floor}`}
          onPress={open}
          style={({ pressed }) => ({
            flex: 1,
            gap: s.sm,
            opacity: pressed ? 0.7 : 1,
          })}
        >
          <Copy variant="heading">{location.name}</Copy>
          <Copy muted variant="caption">
            {location.floor} · {formatWalkingDistance(location.walkingMinutes)}{" "}
            · {location.noiseLevel}
          </Copy>
          <OccupancyBadge percent={location.currentOccupancy} />
        </Pressable>
        <FavoriteButton id={location.id} />
      </View>
    );
  return (
    <View
      style={{
        borderRadius: r.lg,
        overflow: "hidden",
        borderWidth: 1,
        borderColor: c.border,
        backgroundColor: c.surface,
        marginBottom: s.lg,
      }}
    >
      <View>
        <Pressable
          onPress={open}
          accessibilityRole="button"
          accessibilityLabel={`View ${location.name}, ${location.floor}`}
        >
          <LocationImage location={location}>
            <View style={styles.row}>
              <View
                style={{
                  backgroundColor: c.background,
                  paddingHorizontal: s.md,
                  paddingVertical: s.xs,
                  borderRadius: r.pill,
                }}
              >
                <Copy variant="caption">{location.floor}</Copy>
              </View>
            </View>
            <View>
              <Copy variant="heading">{location.name}</Copy>
              <Copy variant="caption" muted>
                GEORGE MASON UNIVERSITY
              </Copy>
            </View>
          </LocationImage>
        </Pressable>
        <View style={{ position: "absolute", top: s.md, right: s.md }}>
          <FavoriteButton id={location.id} />
        </View>
      </View>
      <Pressable
        onPress={open}
        accessibilityRole="button"
        accessibilityLabel={`See details for ${location.name}`}
        style={({ pressed }) => ({
          padding: s.lg,
          gap: s.md,
          opacity: pressed ? 0.7 : 1,
        })}
      >
        <View
          style={[
            styles.row,
            { justifyContent: "space-between", flexWrap: "wrap" },
          ]}
        >
          <OccupancyBadge percent={location.currentOccupancy} />
          <Copy variant="caption" muted>
            {formatWalkingDistance(location.walkingMinutes)}
          </Copy>
        </View>
        <OccupancyBar percent={location.currentOccupancy} />
        <Copy variant="caption" muted>
          {location.noiseLevel.charAt(0).toUpperCase() +
            location.noiseLevel.slice(1)}{" "}
          · {location.amenities.slice(0, 2).join(" · ")}
        </Copy>
      </Pressable>
    </View>
  );
}
export function CompactLocationCard({ location }: { location: StudyLocation }) {
  return <LocationCard location={location} compact />;
}
