import { View } from "react-native";
import { Copy } from "../common";
import { colors, radius, spacing } from "../../theme";
export function RecommendationScore({ score }: { score: number }) {
  return (
    <View
      style={{
        alignSelf: "flex-start",
        padding: spacing.md,
        borderRadius: radius.md,
        backgroundColor: colors.surfaceElevated,
      }}
    >
      <Copy color={colors.primary} style={{ fontWeight: "700" }}>
        {score}% MATCH
      </Copy>
    </View>
  );
}
