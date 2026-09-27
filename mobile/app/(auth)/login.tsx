import { useState } from "react";
import { router } from "expo-router";
import { View } from "react-native";
import {
  Button,
  Card,
  Copy,
  Icon,
  Screen,
  ScreenHeader,
  DemoNote,
} from "../../components/common";
import { colors as c, spacing as s } from "../../theme";
import { useAuth } from "../../store/AuthProvider";
import { authError } from "../../services/auth/errors";
export default function Login() {
  const { oauth } = useAuth();
  const [busy, setBusy] = useState<"google" | "apple" | null>(null);
  const [error, setError] = useState<string>();
  const withProvider = async (provider: "google" | "apple") => {
    setBusy(provider);
    setError(undefined);
    try {
      await oauth(provider);
    } catch (e) {
      setError(authError(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <Screen>
      <ScreenHeader
        title="Your focus starts here."
        subtitle="One campus. So many possibilities."
        back
      />
      <View style={{ alignItems: "center", paddingVertical: s["3xl"] }}>
        <Icon name="leaf" size={80} color={c.primary} />
        <Copy variant="title" style={{ marginTop: s.lg }}>
          studyspot
        </Copy>
      </View>
      <Card>
        <Copy variant="heading">Welcome to your campus companion</Copy>
        <Copy muted>Sign in to save favorites and study preferences.</Copy>
        <Button
          label="Continue with Mason"
          icon="school-outline"
          onPress={() => void withProvider("google")}
          disabled={busy !== null}
          loading={busy === "google"}
        />
        <Button
          label="Continue with Apple"
          icon="logo-apple"
          onPress={() => void withProvider("apple")}
          disabled={busy !== null}
          loading={busy === "apple"}
          secondary
        />
        <Button
          label="Continue with Email"
          icon="mail-outline"
          onPress={() => router.push("/(auth)/email")}
          disabled={busy !== null}
          secondary
        />
      </Card>
      {error && (
        <Copy color={c.danger} style={{ marginTop: s.lg }}>
          {error}
        </Copy>
      )}
      <DemoNote text="Mason accounts sign in with Google. StudySpot never sees your password." />
    </Screen>
  );
}
