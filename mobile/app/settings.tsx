import { Switch, View } from "react-native";
import { useLocalSearchParams } from "expo-router";
import {
  Card,
  Chip,
  Copy,
  Icon,
  Screen,
  ScreenHeader,
  styles,
} from "../components/common";
import { useApp } from "../store/AppStore";
import { colors as c } from "../theme";
export default function Settings() {
  const { section } = useLocalSearchParams<{ section: string }>();
  const { notifications, setNotifications } = useApp();
  const title =
    section === "notifications"
      ? "Notification Settings"
      : section === "appearance"
        ? "Appearance"
        : section === "privacy"
          ? "Privacy"
          : "About StudySpot";
  return (
    <Screen>
      <ScreenHeader title={title} back />
      {section === "notifications" ? (
        <Card>
          <View style={[styles.row, { justifyContent: "space-between" }]}>
            <Copy style={{ flex: 1 }}>Campus updates</Copy>
            <Switch
              accessibilityLabel="Campus updates"
              value={notifications}
              onValueChange={setNotifications}
              trackColor={{ false: c.border, true: c.primary }}
              thumbColor={c.textPrimary}
            />
          </View>
          <Copy muted>
            Show sample occupancy alerts in the Alerts tab. This setting stays
            on your device. Real push notifications are not connected.
          </Copy>
        </Card>
      ) : section === "appearance" ? (
        <Card>
          <Icon name="moon-outline" size={40} color={c.primary} />
          <Copy variant="heading">Campus night</Copy>
          <Chip label="Dark forest · Active" selected />
          <Copy muted>
            Calm colors, clear contrast, and a little room to breathe, built
            around our signature dark appearance.
          </Copy>
        </Card>
      ) : section === "privacy" ? (
        <Card>
          <Icon name="shield-checkmark-outline" size={40} color={c.primary} />
          <Copy variant="heading">Your account data.</Copy>
          <Copy muted>
            Preferences and favorites are stored with your StudySpot account.
            Notification settings stay on this device. Check-ins, reports, and
            recent spaces last only for your current session.
          </Copy>
          <Copy muted>
            Passwords are handled by Supabase and are never sent to StudySpot.
            Foreground location is optional. Coordinates stay briefly in memory
            and are sent to StudySpot for nearby search, without being saved to
            your account. Map tiles come from the configured tile provider, and
            optional walking routes use the configured routing provider; those
            providers receive map requests or route endpoints. There is no
            background tracking or movement history. Clearing app data does not
            delete server preferences or favorites.
          </Copy>
        </Card>
      ) : (
        <Card>
          <Icon name="leaf" size={56} color={c.primary} />
          <Copy variant="title">A better place to focus.</Copy>
          <Copy muted>
            StudySpot helps Mason students discover study spaces that fit their
            day. It is built with React Native, Expo, Supabase Auth, and
            FastAPI.
          </Copy>
          <Copy muted>
            Live crowdsourcing and trained forecasts are planned for future
            phases.
          </Copy>
          <Chip label="VERSION 0.4 · PHASE 4" />
        </Card>
      )}
    </Screen>
  );
}
