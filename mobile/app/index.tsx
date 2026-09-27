import { Redirect } from "expo-router";
import { useApp } from "../store/AppStore";
import { useAuth } from "../store/AuthProvider";
import { accountRoute } from "../services/auth/routing";
export default function Index() {
  const { onboardingCompleted } = useApp();
  const auth = useAuth();
  return (
    <Redirect
      href={
        auth.recovery
          ? "/(auth)/reset-password"
          : accountRoute(
              auth.isAuthenticated,
              auth.introComplete,
              onboardingCompleted,
            )
      }
    />
  );
}
