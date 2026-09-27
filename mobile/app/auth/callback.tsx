import { useEffect, useState } from "react";
import * as Linking from "expo-linking";
import { Redirect, router } from "expo-router";
import { Button, Copy, LoadingSkeleton, Screen } from "../../components/common";
import { useAuth } from "../../store/AuthProvider";
import { authError } from "../../services/auth/errors";
// Reached from a Supabase email link or, on web, the OAuth redirect. Native OAuth
// resolves inside AuthProvider.oauth() without ever navigating here.
export default function AuthCallback() {
  const { completeCallback } = useAuth();
  const url = Linking.useURL();
  const [status, setStatus] = useState<"pending" | "done" | "error">("pending");
  const [message, setMessage] = useState<string>();
  useEffect(() => {
    if (!url) return;
    completeCallback(url).then(
      () => setStatus("done"),
      (e) => {
        setMessage(authError(e));
        setStatus("error");
      },
    );
  }, [url, completeCallback]);
  if (status === "done") return <Redirect href="/" />;
  if (status === "error")
    return (
      <Screen>
        <Copy>{message ?? "We couldn't finish signing you in."}</Copy>
        <Button
          label="Back to sign in"
          onPress={() => router.replace("/(auth)/login")}
        />
      </Screen>
    );
  return (
    <Screen>
      <LoadingSkeleton />
    </Screen>
  );
}
