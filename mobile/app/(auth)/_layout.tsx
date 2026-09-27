import { Stack } from "expo-router";
import { useAuth } from "../../store/AuthProvider";
export default function AuthLayout() {
  const auth = useAuth();
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Protected guard={!auth.isAuthenticated}>
        <Stack.Screen name="onboarding" />
        <Stack.Screen name="login" />
        <Stack.Screen name="email" />
        <Stack.Screen name="forgot-password" />
      </Stack.Protected>
      <Stack.Protected guard={auth.isAuthenticated && !auth.recovery}>
        <Stack.Screen name="preferences" />
      </Stack.Protected>
      <Stack.Protected guard={auth.isAuthenticated && auth.recovery}>
        <Stack.Screen name="reset-password" />
      </Stack.Protected>
    </Stack>
  );
}
