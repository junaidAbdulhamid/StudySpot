import { useState } from "react";
import { router } from "expo-router";
import {
  Button,
  Card,
  Copy,
  Screen,
  ScreenHeader,
  TextField,
} from "../../components/common";
import { colors as c, spacing as s } from "../../theme";
import { useAuth } from "../../store/AuthProvider";
import { authError } from "../../services/auth/errors";
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export default function ForgotPassword() {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [sent, setSent] = useState(false);
  const submit = async () => {
    if (!EMAIL_PATTERN.test(email.trim())) {
      setError("Enter a valid email address.");
      return;
    }
    setBusy(true);
    setError(undefined);
    try {
      await forgotPassword(email.trim());
      setSent(true);
    } catch (e) {
      setError(authError(e));
    } finally {
      setBusy(false);
    }
  };
  if (sent)
    return (
      <Screen>
        <ScreenHeader title="Check your inbox." back />
        <Card>
          <Copy>
            If an account exists for {email.trim()}, we sent a link to reset its
            password.
          </Copy>
          <Button
            label="Back to sign in"
            onPress={() => router.replace("/(auth)/login")}
          />
        </Card>
      </Screen>
    );
  return (
    <Screen>
      <ScreenHeader
        title="Reset your password."
        subtitle="We'll email you a link to choose a new one."
        back
      />
      <Card>
        <TextField
          label="Email"
          value={email}
          onChangeText={setEmail}
          placeholder="you@gmu.edu"
          keyboardType="email-address"
          returnKeyType="go"
          onSubmitEditing={() => void submit()}
        />
        <Button
          label="Send Reset Link"
          onPress={() => void submit()}
          disabled={busy}
          loading={busy}
        />
      </Card>
      {error && (
        <Copy color={c.danger} style={{ marginTop: s.lg }}>
          {error}
        </Copy>
      )}
    </Screen>
  );
}
