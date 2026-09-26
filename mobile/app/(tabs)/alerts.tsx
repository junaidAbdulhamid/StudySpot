import { useState } from "react";
import { FlatList, Pressable, View } from "react-native";
import { router } from "expo-router";
import {
  Card,
  Chip,
  Copy,
  DemoNote,
  EmptyState,
  ErrorState,
  Icon,
  LoadingSkeleton,
  Screen,
  ScreenHeader,
  styles,
} from "../../components/common";
import { OccupancyBadge } from "../../components/occupancy";
import { alertService } from "../../services/alertService";
import { useAsync } from "../../hooks/useAsync";
import { useApp } from "../../store/AppStore";
import { colors as c, spacing as s } from "../../theme";
export default function Alerts() {
  const { data, loading, error, retry } = useAsync(alertService.getAlerts);
  const [dismissed, setDismissed] = useState(false);
  const { notifications } = useApp();
  return (
    <Screen scroll={false}>
      <ScreenHeader
        title="A little heads-up."
        subtitle="Good timing makes all the difference."
      />
      <View
        style={[
          styles.row,
          { justifyContent: "space-between", marginBottom: s.lg },
        ]}
      >
        <Copy variant="label" color={c.primary}>
          CAMPUS UPDATES
        </Copy>
        <Chip
          label={dismissed ? "Restore demo" : "Clear all"}
          onPress={() => setDismissed(!dismissed)}
        />
      </View>
      {loading ? (
        <LoadingSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <FlatList
          data={dismissed || !notifications ? [] : data}
          keyExtractor={(a) => a.id}
          renderItem={({ item }) => (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`View ${item.title}`}
              onPress={() => router.push(`/location/${item.locationId}`)}
              style={({ pressed }) => ({
                opacity: pressed ? 0.7 : 1,
                marginBottom: s.lg,
              })}
            >
              <Card>
                <View style={styles.row}>
                  <Icon name="notifications-outline" color={c.primary} />
                  <Copy muted variant="caption">
                    {item.timestamp}
                  </Copy>
                </View>
                <Copy variant="heading">{item.title}</Copy>
                <Copy muted>{item.message}</Copy>
                <OccupancyBadge percent={item.percent} />
              </Card>
            </Pressable>
          )}
          ListEmptyComponent={
            <EmptyState
              title="All quiet for now."
              message={
                notifications
                  ? "You’re all caught up. Restore the demo to see sample updates."
                  : "Campus updates are paused. You can enable them in notification settings."
              }
              icon="notifications-off-outline"
            />
          }
          ListFooterComponent={
            <DemoNote text="Sample notifications only. Push delivery and background monitoring arrive in a future phase." />
          }
        />
      )}
    </Screen>
  );
}
