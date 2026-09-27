import { Pressable, View } from "react-native";
import { useState } from "react";
import { router } from "expo-router";
import {
  Avatar,
  Button,
  Card,
  Chip,
  Copy,
  DemoNote,
  Icon,
  IconName,
  Screen,
  SectionHeader,
  styles,
} from "../../components/common";
import { useApp } from "../../store/AppStore";
import { colors as c, spacing as s } from "../../theme";
import { authError } from "../../services/auth/errors";
export default function Profile() {
  const { preferences, favorites, logout, storageError, user } = useApp();
  const [signingOut, setSigningOut] = useState(false);
  const [confirmingSignOut, setConfirmingSignOut] = useState(false);
  const [signOutError, setSignOutError] = useState<string>();
  return (
    <Screen>
      <Copy variant="title" style={{ marginBottom: s.xl }}>
        Your space.
      </Copy>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Edit profile"
        onPress={() => router.push("/edit-profile")}
      >
        <Card>
          <View style={styles.row}>
            <Avatar name={user.name} />
            <View style={{ flex: 1 }}>
              <Copy variant="heading">{user.name}</Copy>
              <Copy muted variant="caption">
                {user.email}
              </Copy>
            </View>
            <Icon name="chevron-forward" size={18} color={c.textMuted} />
          </View>
          <Chip label="MASON STUDENT" icon="school-outline" />
          <Copy muted variant="caption">
            {favorites.length} saved{" "}
            {favorites.length === 1 ? "location" : "locations"}
          </Copy>
        </Card>
      </Pressable>
      <SectionHeader
        title="Your study rhythm"
        action="Edit"
        onPress={() => router.push("/(auth)/preferences?edit=1")}
      />
      <View style={styles.wrap}>
        <Chip
          label={preferences.noise === "any" ? "Any noise" : preferences.noise}
        />
        <Chip label={preferences.studyType} />
        {preferences.amenities.map((a) => (
          <Chip key={a} label={a} />
        ))}
        <Chip
          label={
            preferences.maxWalk === 99
              ? "Any walking distance"
              : `${preferences.maxWalk}-minute walking radius`
          }
        />
      </View>
      <SectionHeader title="Make it yours" />
      <Card>
        {(
          [
            {
              label: "Study Preferences",
              icon: "options-outline",
              href: "/(auth)/preferences?edit=1",
            },
            { label: "Favorites", icon: "heart-outline", href: "/favorites" },
            {
              label: "Notification Settings",
              icon: "notifications-outline",
              href: "/settings?section=notifications",
            },
            {
              label: "Appearance",
              icon: "moon-outline",
              href: "/settings?section=appearance",
            },
            {
              label: "Privacy",
              icon: "shield-checkmark-outline",
              href: "/settings?section=privacy",
            },
            {
              label: "About StudySpot",
              icon: "information-circle-outline",
              href: "/settings?section=about",
            },
          ] as const
        ).map((row) => (
          <Pressable
            key={row.label}
            accessibilityRole="button"
            onPress={() => router.push(row.href)}
            style={({ pressed }) => [
              styles.row,
              { minHeight: 52, opacity: pressed ? 0.6 : 1 },
            ]}
          >
            <Icon name={row.icon as IconName} color={c.textSecondary} />
            <Copy style={{ flex: 1 }}>{row.label}</Copy>
            <Icon name="chevron-forward" size={18} color={c.textMuted} />
          </Pressable>
        ))}
      </Card>
      <View style={{ marginTop: s.xl }}>
        {confirmingSignOut ? (
          <Card>
            <Copy variant="heading">Log out?</Copy>
            <Copy muted>You’ll need to sign in again on this device.</Copy>
            <Button
              label="Confirm Log Out"
              icon="log-out-outline"
              loading={signingOut}
              onPress={async () => {
                setSigningOut(true);
                setSignOutError(undefined);
                try {
                  await logout();
                } catch (error) {
                  setSignOutError(authError(error));
                } finally {
                  setSigningOut(false);
                }
              }}
            />
            <Button
              label="Cancel"
              secondary
              onPress={() => setConfirmingSignOut(false)}
            />
          </Card>
        ) : (
          <Button
            label="Log Out"
            secondary
            icon="log-out-outline"
            onPress={() => setConfirmingSignOut(true)}
          />
        )}
      </View>
      {signOutError && <Copy color={c.danger}>{signOutError}</Copy>}
      {storageError && (
        <Copy color={c.warning} style={{ marginTop: s.lg }}>
          {storageError}
        </Copy>
      )}
      <DemoNote text="StudySpot · Your preferences and favorites follow your account." />
    </Screen>
  );
}
