import { Recommendation, StudyLocation, UserPreferences } from "../types";
export function rankLocations(
  locations: StudyLocation[],
  prefs: UserPreferences,
): Recommendation[] {
  return locations
    .filter(
      (l) =>
        (l.walkingMinutes === null || l.walkingMinutes <= prefs.maxWalk) &&
        prefs.amenities.every((a) => l.amenities.includes(a)),
    )
    .map((location) => {
      const point =
        location.predictions.find((p) => p.hoursAhead >= prefs.duration) ??
        location.predictions.at(-1);
      const expectedOccupancy = point?.percent ?? null;
      const quietMatch =
        prefs.noise === "any" || prefs.noise === location.noiseLevel;
      const studyMatch =
        prefs.studyType === "either" ||
        (prefs.studyType === "group"
          ? location.amenities.includes("Group rooms") ||
            location.amenities.includes("Large tables")
          : location.noiseLevel === "quiet");
      const crowd =
        location.currentOccupancy === null
          ? 0
          : 35 *
            (1 -
              (location.currentOccupancy +
                (expectedOccupancy ?? location.currentOccupancy)) /
                200);
      const distance =
        location.walkingMinutes === null
          ? 0
          : 20 * (1 - Math.min(location.walkingMinutes, 20) / 25);
      const weight = location.walkingMinutes === null ? 80 : 100;
      const score = Math.round(
        ((crowd +
          25 * Number(quietMatch) +
          20 * Number(studyMatch) +
          distance) *
          100) /
          weight,
      );
      return {
        location,
        score: Math.max(0, Math.min(100, score)),
        expectedOccupancy,
        reasons: [
          quietMatch ? "Fits your noise preference" : "A livelier alternative",
          studyMatch ? "Made for your study style" : "Try a different setting",
          "All must-have amenities",
        ],
      };
    })
    .sort(
      (a, b) => b.score - a.score || a.location.id.localeCompare(b.location.id),
    );
}
