import { Redirect } from "expo-router";
import { useApp } from "../store/AppStore";
export default function Index() {
  const { signedIn } = useApp();
  return <Redirect href={signedIn ? "/(tabs)" : "/(auth)/onboarding"} />;
}
