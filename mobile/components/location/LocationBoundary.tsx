import React from "react";
import { router } from "expo-router";
import { EmptyState, ErrorState, LoadingSkeleton, Screen } from "../common";
import { StudyLocation } from "../../types";
export function LocationBoundary({
  state,
  children,
}: {
  state: {
    data: StudyLocation | undefined;
    loading: boolean;
    error: string | undefined;
    retry: () => void;
  };
  children: (location: StudyLocation) => React.ReactNode;
}) {
  if (state.loading)
    return (
      <Screen>
        <LoadingSkeleton />
      </Screen>
    );
  if (state.error)
    return (
      <Screen>
        <ErrorState message={state.error} onRetry={state.retry} />
      </Screen>
    );
  if (!state.data)
    return (
      <Screen>
        <EmptyState
          title="Space not found"
          message="This study zone is not part of the demo campus."
          action="Explore spaces"
          onAction={() => router.replace("/(tabs)/explore")}
        />
      </Screen>
    );
  return <>{children(state.data)}</>;
}
