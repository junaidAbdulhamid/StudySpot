import { useState } from "react";
import { View } from "react-native";
import { router } from "expo-router";
import {
  Button,
  Card,
  Copy,
  Icon,
  Screen,
  ScreenHeader,
} from "../../components/common";
import { PreferenceFields } from "../../components/common/PreferenceFields";
import { useApp } from "../../store/AppStore";
import { colors as c, spacing as s } from "../../theme";
export default function FindSpot() {
  const { preferences, savePreferences } = useApp();
  const [saving, setSaving] = useState(false);
  const [value, setValue] = useState(preferences);
  return (
    <Screen>
      <ScreenHeader
        title="Let’s find your spot."
        subtitle="A little about your session. A space that fits."
        back
      />
      <Card style={{ marginBottom: s["2xl"] }}>
        <Icon name="sparkles-outline" color={c.primary} />
        <Copy muted>
          We’ll balance available crowd estimates and your study style.
          Must-haves stay must-haves. With location enabled, walking preferences
          use real routes where available, otherwise a clearly labeled
          geographic radius.
        </Copy>
      </Card>
      <PreferenceFields value={value} onChange={setValue} includeDuration />
      <View style={{ marginTop: s.md }}>
        <Button
          label="Find My Spot"
          icon="sparkles-outline"
          loading={saving}
          onPress={async () => {
            setSaving(true);
            const saved = await savePreferences(value);
            setSaving(false);
            if (!saved) return;
            router.push("/find-spot/results");
          }}
        />
      </View>
    </Screen>
  );
}
