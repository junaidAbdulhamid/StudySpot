import {
  DarkTheme,
  Redirect,
  Stack,
  ThemeProvider,
  useGlobalSearchParams,
  useSegments,
} from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AppProvider, useApp } from "../store/AppStore";
import { colors } from "../theme";
import { AuthProvider, useAuth } from "../store/AuthProvider";
import { LoadingSkeleton, Screen, Copy, Button } from "../components/common";
function Navigation() {
  const { ready, signedIn, profileError, reloadProfile, onboardingCompleted } =
    useApp();
  const auth = useAuth();
  const segments = useSegments();
  const { edit } = useGlobalSearchParams<{ edit?: string }>();
  if (auth.loading || !ready)
    return (
      <Screen>
        <LoadingSkeleton />
      </Screen>
    );
  if (auth.error && !auth.session)
    return (
      <Screen>
        <Copy>{auth.error}</Copy>
        <Button label="Retry" onPress={() => void auth.bootstrap()} />
      </Screen>
    );
  if (auth.isAuthenticated && profileError)
    return (
      <Screen>
        <Copy>{profileError}</Copy>
        <Button label="Retry" onPress={() => void reloadProfile()} />
        <Button
          label="Sign out"
          secondary
          onPress={() => void auth.signOut().catch(() => {})}
        />
      </Screen>
    );
  if (auth.isAuthenticated && !signedIn)
    return (
      <Screen>
        <LoadingSkeleton />
      </Screen>
    );
  if (signedIn && !onboardingCompleted && segments[0] !== "(auth)")
    return <Redirect href="/(auth)/preferences" />;
  if (
    signedIn &&
    onboardingCompleted &&
    segments[0] === "(auth)" &&
    !auth.recovery &&
    edit !== "1"
  )
    return <Redirect href="/(tabs)" />;
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      <Stack.Screen name="index" />
      <Stack.Screen name="(auth)" />
      <Stack.Screen name="auth/callback" />
      <Stack.Protected guard={signedIn && !auth.recovery}>
        <Stack.Screen name="edit-profile" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="location/[id]" />
        <Stack.Screen name="predictions/[id]" />
        <Stack.Screen name="report/[id]" />
        <Stack.Screen name="find-spot/index" />
        <Stack.Screen name="find-spot/results" />
        <Stack.Screen name="favorites" />
        <Stack.Screen name="recent" />
        <Stack.Screen name="settings" />
        <Stack.Screen name="directions/[id]" />
      </Stack.Protected>
    </Stack>
  );
}
export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ThemeProvider
        value={{
          ...DarkTheme,
          colors: {
            ...DarkTheme.colors,
            background: colors.background,
            card: colors.surface,
            primary: colors.primary,
            text: colors.textPrimary,
            border: colors.border,
          },
        }}
      >
        <AuthProvider>
          <AppProvider>
            <StatusBar style="light" />
            <Navigation />
          </AppProvider>
        </AuthProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
