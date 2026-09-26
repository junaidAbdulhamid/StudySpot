import { Stack, ThemeProvider, DarkTheme } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AppProvider, useApp } from "../store/AppStore";
import { colors } from "../theme";
import { LoadingSkeleton, Screen } from "../components/common";
function Navigation() {
  const { ready, signedIn } = useApp();
  if (!ready)
    return (
      <Screen>
        <LoadingSkeleton />
      </Screen>
    );
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      <Stack.Screen name="index" />
      <Stack.Screen name="(auth)" />
      <Stack.Protected guard={signedIn}>
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
        <AppProvider>
          <StatusBar style="light" />
          <Navigation />
        </AppProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
