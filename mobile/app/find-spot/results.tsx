import { useCallback } from "react";
import { View } from "react-native";
import { router } from "expo-router";
import {
  Button,
  Card,
  Copy,
  DemoNote,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  Screen,
  ScreenHeader,
  styles,
} from "../../components/common";
import { LocationCard } from "../../components/location";
import { PredictionBadge } from "../../components/occupancy";
import { RecommendationScore } from "../../components/recommendations/RecommendationScore";
import { recommendationService } from "../../services/recommendationService";
import { useAsync } from "../../hooks/useAsync";
import { useApp } from "../../store/AppStore";
import { useDeviceLocation } from "../../store/LocationProvider";
import { colors as c, spacing as s } from "../../theme";
export default function Results() {
  const { preferences } = useApp();
  const { coordinates } = useDeviceLocation();
  const loader = useCallback(async () => {
    const [results] = await Promise.all([
      recommendationService.getRecommendations(preferences, coordinates),
      new Promise((resolve) => setTimeout(resolve, 650)),
    ]);
    return results;
  }, [preferences, coordinates]);
  const { data, loading, error, retry } = useAsync(loader);
  return (
    <Screen>
      <ScreenHeader
        title="Good spaces. Great focus."
        subtitle="Your top matches, made for this session."
        back
      />
      <Copy muted>
        {coordinates
          ? `Proximity fallback: searching within ${Math.min(10000, preferences.maxWalk * 60)} m straight-line. This is not a ${preferences.maxWalk}-minute walking guarantee.`
          : "Location unavailable: walking constraints cannot be applied. Enable location on Home for proximity filtering."}
      </Copy>
      {loading ? (
        <>
          <Copy color={c.primary}>Finding your best study spots...</Copy>
          <LoadingSkeleton />
        </>
      ) : error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : data?.length ? (
        <>
          {data.slice(0, 3).map((result, i) => (
            <Card
              key={result.location.id}
              style={{
                marginBottom: s.xl,
                borderColor: i === 0 ? c.primary : c.border,
                padding: s.lg,
              }}
            >
              <View
                style={[
                  styles.row,
                  { justifyContent: "space-between", flexWrap: "wrap" },
                ]}
              >
                <Copy
                  variant="label"
                  color={i === 0 ? c.primary : c.textSecondary}
                >
                  #{i + 1} {i === 0 ? "BEST MATCH" : "A GREAT ALTERNATIVE"}
                </Copy>
                <RecommendationScore score={result.score} />
              </View>
              <LocationCard location={result.location} />
              <PredictionBadge percent={result.expectedOccupancy} />
              <Copy muted variant="caption">
                At the end of your{" "}
                {preferences.duration === 0.5
                  ? "30-minute"
                  : `${preferences.duration}-hour`}{" "}
                session
              </Copy>
              <Copy muted variant="caption">
                {result.reasons.join(" · ")}
              </Copy>
            </Card>
          ))}
          <DemoNote text="Demo match scores use your selections and persisted seed forecasts. Distance is not scored. No ML model is connected." />
          <Button
            label="Adjust my session"
            secondary
            onPress={() => router.back()}
          />
        </>
      ) : (
        <EmptyState
          title="Let’s give you more options"
          message="No spaces meet all your must-haves. Try fewer amenities or a wider proximity range."
          action="Adjust preferences"
          onAction={() => router.back()}
        />
      )}
    </Screen>
  );
}
