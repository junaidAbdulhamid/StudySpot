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
            Calm colors, clear contrast, and a little room to breathe. Phase 2
            is designed around our signature dark appearance.
          </Copy>
        </Card>
      ) : section === "privacy" ? (
        <Card>
          <Icon name="shield-checkmark-outline" size={40} color={c.primary} />
          <Copy variant="heading">Your development data.</Copy>
          <Copy muted>
            Preferences and favorites are stored in the development database.
            Notification settings stay on this device. Check-ins, reports, and
            recent spaces last only for your current session.
          </Copy>
          <Copy muted>
            No account credentials, GPS location, analytics, or crowd reports
            are collected. Preferences and favorites are sent to your configured
            API. Campus estimates and forecasts are seeded examples. Clearing
            app data does not delete server preferences or favorites.
          </Copy>
        </Card>
      ) : (
        <Card>
          <Icon name="leaf" size={56} color={c.primary} />
          <Copy variant="title">A better place to focus.</Copy>
          <Copy muted>
            StudySpot helps Mason students discover study spaces that fit their
            day. Phase 2 is an interactive product preview, built with React
            Native and Expo.
          </Copy>
          <Copy muted>
            Live crowdsourcing, accounts, real maps, and personalized forecasts
            are planned for future phases.
          </Copy>
          <Chip label="VERSION 0.2 · PHASE 2" />
        </Card>
      )}
    </Screen>
  );
}
