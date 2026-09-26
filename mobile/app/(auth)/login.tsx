import { useState } from "react";
import { errorMessage } from "../../services/api/client";
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
import { useApp } from "../../store/AppStore";
export default function Login() {
  const { login } = useApp();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const enter = async () => {
    setBusy(true);
    setError(undefined);
    try {
      await login();
      router.replace("/(auth)/preferences");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
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
        <Copy muted>
          Explore the development preview with a demo account. Choose any option
          to continue.
        </Copy>
        <Button
          label="Continue with Mason"
          icon="school-outline"
          onPress={enter}
          disabled={busy}
        />
        <Button
          label="Continue with Google"
          icon="logo-google"
          onPress={enter}
          disabled={busy}
          secondary
        />
        <Button
          label="Continue with Apple"
          icon="logo-apple"
          onPress={enter}
          disabled={busy}
          secondary
        />
        <Button
          label="Continue with Email"
          icon="mail-outline"
          onPress={enter}
          disabled={busy}
          secondary
        />
      </Card>
      {error && (
        <Copy color={c.danger} style={{ marginTop: s.lg }}>
          {error}
        </Copy>
      )}
      {busy && <Copy muted>Connecting to your development profile…</Copy>}
      <DemoNote text="Demo sign-in only. No credentials are collected and no provider account is connected." />
    </Screen>
  );
}
