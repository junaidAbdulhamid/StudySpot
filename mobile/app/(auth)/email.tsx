import { useState } from "react";
import { Pressable, View } from "react-native";
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
export default function Email() {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [confirmSent, setConfirmSent] = useState(false);
  const submit = async () => {
    setError(undefined);
    if (!EMAIL_PATTERN.test(email.trim())) {
      setError("Enter a valid email address.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "signin") {
        await signIn(email.trim(), password);
      } else {
        const hasSession = await signUp(email.trim(), password);
        if (!hasSession) setConfirmSent(true);
      }
    } catch (e) {
      setError(authError(e));
    } finally {
      setBusy(false);
    }
  };
  if (confirmSent)
    return (
      <Screen>
        <ScreenHeader title="Check your inbox." back />
        <Card>
          <Copy>
            We sent a confirmation link to {email.trim()}. Follow it to finish
            creating your account.
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
        title={
          mode === "signin" ? "Sign in with email." : "Create your account."
        }
        back
      />
      <Card>
        <TextField
          label="Email"
          value={email}
          onChangeText={setEmail}
          placeholder="you@gmu.edu"
          keyboardType="email-address"
          returnKeyType="next"
        />
        <TextField
          label="Password"
          value={password}
          onChangeText={setPassword}
          placeholder="••••••••"
          secureTextEntry
          returnKeyType="go"
          onSubmitEditing={() => void submit()}
        />
        {mode === "signin" && (
          <Pressable
            accessibilityRole="button"
            onPress={() => router.push("/(auth)/forgot-password")}
            style={{ minHeight: 32, justifyContent: "center" }}
          >
            <Copy variant="caption" color={c.primary}>
              Forgot password?
            </Copy>
          </Pressable>
        )}
        <Button
          label={mode === "signin" ? "Sign In" : "Create Account"}
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
      <View style={{ alignItems: "center", marginTop: s.xl }}>
        <Pressable
          accessibilityRole="button"
          onPress={() => {
            setError(undefined);
            setMode((m) => (m === "signin" ? "signup" : "signin"));
          }}
          style={{ minHeight: 44, justifyContent: "center" }}
        >
          <Copy muted>
            {mode === "signin"
              ? "Don't have an account? "
              : "Already have an account? "}
            <Copy color={c.primary}>
              {mode === "signin" ? "Sign up" : "Sign in"}
            </Copy>
          </Copy>
        </Pressable>
      </View>
    </Screen>
  );
}
