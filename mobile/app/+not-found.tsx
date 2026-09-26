import { router } from "expo-router";
import { EmptyState, Screen } from "../components/common";
export default function NotFound() {
  return (
    <Screen>
      <EmptyState
        title="A little off campus."
        message="This page doesn’t exist. Let’s get you back to a familiar spot."
        action="Go to StudySpot"
        onAction={() => router.replace("/")}
      />
    </Screen>
  );
}
