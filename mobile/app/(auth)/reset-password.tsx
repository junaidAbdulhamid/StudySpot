import { useState } from "react";
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
export default function ResetPassword() {
  const { resetPassword } = useAuth();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const submit = async () => {
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }
    setBusy(true);
    setError(undefined);
    try {
      await resetPassword(password);
    } catch (e) {
      setError(authError(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Screen>
      <ScreenHeader
        title="Choose a new password."
        subtitle="You'll use this the next time you sign in with email."
      />
      <Card>
        <TextField
          label="New password"
          value={password}
          onChangeText={setPassword}
          placeholder="••••••••"
          secureTextEntry
          returnKeyType="next"
        />
        <TextField
          label="Confirm password"
          value={confirm}
          onChangeText={setConfirm}
          placeholder="••••••••"
          secureTextEntry
          returnKeyType="go"
          onSubmitEditing={() => void submit()}
        />
        <Button
          label="Save Password"
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
