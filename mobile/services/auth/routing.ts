export function accountRoute(
  authenticated: boolean,
  introComplete: boolean,
  onboardingComplete: boolean,
) {
  if (!authenticated)
    return introComplete ? "/(auth)/login" : "/(auth)/onboarding";
  return onboardingComplete ? "/(tabs)" : "/(auth)/preferences";
}
