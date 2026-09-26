import { View } from "react-native";
import { UserPreferences, Amenity } from "../../types";
import { Chip, Copy, styles } from "./index";
import { spacing } from "../../theme";
export const amenityOptions: Amenity[] = [
  "Outlets",
  "Whiteboards",
  "Large tables",
  "Food nearby",
  "Printers",
  "Natural light",
  "Group rooms",
];
export function PreferenceFields({
  value,
  onChange,
  step,
  includeDuration = false,
}: {
  value: UserPreferences;
  onChange: (v: UserPreferences) => void;
  step?: number;
  includeDuration?: boolean;
}) {
  const update = (patch: Partial<UserPreferences>) =>
    onChange({ ...value, ...patch });
  const section = (title: string, children: React.ReactNode) => (
    <View style={{ gap: spacing.md, marginBottom: spacing.xl }}>
      <Copy variant="label" muted>
        {title}
      </Copy>
      <View style={styles.wrap}>{children}</View>
    </View>
  );
  return (
    <>
      {includeDuration &&
        section(
          "STUDY DURATION",
          [0.5, 1, 2, 3].map((n, i) => (
            <Chip
              key={n}
              label={["30 min", "1 hour", "2 hours", "3+ hours"][i]!}
              selected={value.duration === n}
              onPress={() => update({ duration: n })}
            />
          )),
        )}
      {(step === undefined || step === 0) &&
        section(
          "HOW QUIET DO YOU LIKE IT?",
          (["quiet", "moderate", "any"] as const).map((n, i) => (
            <Chip
              key={n}
              label={["Quiet", "Moderate", "Doesn’t matter"][i]!}
              selected={value.noise === n}
              onPress={() => update({ noise: n })}
            />
          )),
        )}
      {(step === undefined || step === 1) &&
        section(
          "HOW DO YOU USUALLY STUDY?",
          (["solo", "group", "either"] as const).map((n, i) => (
            <Chip
              key={n}
              label={["Solo", "Group", "Both"][i]!}
              selected={value.studyType === n}
              onPress={() => update({ studyType: n })}
            />
          )),
        )}
      {(step === undefined || step === 2) &&
        section(
          "YOUR MUST-HAVES",
          amenityOptions.map((a) => (
            <Chip
              key={a}
              label={a}
              selected={value.amenities.includes(a)}
              onPress={() =>
                update({
                  amenities: value.amenities.includes(a)
                    ? value.amenities.filter((x) => x !== a)
                    : [...value.amenities, a],
                })
              }
            />
          )),
        )}
      {(step === undefined || step === 3) &&
        section(
          "HOW FAR WILL YOU WALK?",
          [5, 10, 15, 99].map((n) => (
            <Chip
              key={n}
              label={n === 99 ? "Any distance" : `${n} minutes`}
              selected={value.maxWalk === n}
              onPress={() => update({ maxWalk: n })}
            />
          )),
        )}
    </>
  );
}
