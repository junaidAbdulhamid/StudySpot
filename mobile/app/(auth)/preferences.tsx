import { useState } from "react";
import { View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import {
  Button,
  Card,
  Copy,
  Icon,
  Screen,
  ScreenHeader,
  styles,
} from "../../components/common";
import { PreferenceFields } from "../../components/common/PreferenceFields";
import { useApp } from "../../store/AppStore";
import { colors as c, spacing as s } from "../../theme";
export default function Preferences() {
  const { preferences, savePreferences } = useApp();
  const { edit } = useLocalSearchParams<{ edit?: string }>();
  const [value, setValue] = useState(preferences);
  const [saving, setSaving] = useState(false);
  const [step, setStep] = useState(0);
  return (
    <Screen>
      <ScreenHeader
        title="Make it your space."
        subtitle="A few little details. Better recommendations."
        back={!!edit}
      />
      <View style={[styles.row, { marginBottom: s["2xl"] }]}>
        {[0, 1, 2, 3].map((i) => (
          <View
            key={i}
            style={{
              flex: 1,
              height: 4,
              backgroundColor: i <= step ? c.primary : c.border,
              borderRadius: 4,
            }}
          />
        ))}
      </View>
      <Copy variant="label" color={c.primary}>
        STEP {step + 1} OF 4
      </Copy>
      <View style={{ paddingVertical: s["2xl"] }}>
        <Icon
          name={
            (
              [
                "volume-low-outline",
                "people-outline",
                "flash-outline",
                "walk-outline",
              ] as const
            )[step]!
          }
          size={56}
          color={c.primary}
        />
      </View>
      <PreferenceFields value={value} onChange={setValue} step={step} />
      <Card>
        <Copy muted>
          Preferences are saved to your development profile in StudySpot’s
          database. Walking preferences are reserved for a future phase.
        </Copy>
      </Card>
      <View style={{ gap: s.md, marginTop: s["2xl"] }}>
        <Button
          label={step === 3 ? "Finish" : "Next"}
          loading={saving}
          onPress={async () => {
            if (step < 3) setStep(step + 1);
            else {
              setSaving(true);
              const saved = await savePreferences(value);
              setSaving(false);
              if (!saved) return;
              if (edit) router.back();
              else router.replace("/(tabs)");
            }
          }}
        />
        {step > 0 && (
          <Button label="Back" secondary onPress={() => setStep(step - 1)} />
        )}
      </View>
    </Screen>
  );
}
