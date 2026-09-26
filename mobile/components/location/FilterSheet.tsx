import { Modal, ScrollView, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button, Chip, Copy, IconButton, styles } from "../common";
import { amenityOptions } from "../common/PreferenceFields";
import { LocationFilters } from "../../types";
import { colors as c, spacing as s, radius as r } from "../../theme";
// Distance is deliberately absent: no walking time exists until Phase 4 proximity search.
export type FilterKind = "Crowding" | "Noise" | "Amenities";
export function FilterSheet({
  kind,
  onClose,
  value,
  onChange,
}: {
  kind: FilterKind | null;
  onClose: () => void;
  value: LocationFilters;
  onChange: (value: LocationFilters) => void;
}) {
  const update = (patch: Partial<LocationFilters>) =>
    onChange({ ...value, ...patch });
  return (
    <Modal
      visible={kind !== null}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View
        style={{
          flex: 1,
          justifyContent: "flex-end",
          backgroundColor: c.scrim,
        }}
      >
        <SafeAreaView
          edges={["bottom"]}
          style={{
            backgroundColor: c.surface,
            borderTopLeftRadius: r.xl,
            borderTopRightRadius: r.xl,
            maxHeight: "85%",
          }}
        >
          <ScrollView contentContainerStyle={{ padding: s.xl, gap: s.xl }}>
            <View style={[styles.row, { justifyContent: "space-between" }]}>
              <Copy variant="title">{kind}</Copy>
              <IconButton
                icon="close"
                label="Close filters"
                onPress={onClose}
              />
            </View>
            <View style={styles.wrap}>
              {kind === "Crowding" &&
                (["any", "available", "moderate", "busy", "full"] as const).map(
                  (x) => (
                    <Chip
                      key={x}
                      label={
                        x === "any"
                          ? "Any crowd level"
                          : x === "full"
                            ? "Nearly full"
                            : x.charAt(0).toUpperCase() + x.slice(1)
                      }
                      selected={value.crowding === x}
                      onPress={() => update({ crowding: x })}
                    />
                  ),
                )}
              {kind === "Noise" &&
                (["any", "quiet", "moderate", "social"] as const).map((x) => (
                  <Chip
                    key={x}
                    label={
                      x === "any"
                        ? "Any noise level"
                        : x.charAt(0).toUpperCase() + x.slice(1)
                    }
                    selected={value.noise === x}
                    onPress={() => update({ noise: x })}
                  />
                ))}
              {kind === "Amenities" &&
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
                ))}
            </View>
            <Button label="Show study spaces" onPress={onClose} />
          </ScrollView>
        </SafeAreaView>
      </View>
    </Modal>
  );
}
