import { router } from "expo-router";
import {
  Button,
  Card,
  Copy,
  DemoNote,
  Screen,
  ScreenHeader,
} from "../../components/common";
import { LocationBoundary } from "../../components/location/LocationBoundary";
import { CampusMap } from "../../components/navigation/CampusMap";
import { useLocation } from "../../hooks/useLocation";
export default function Directions() {
  const state = useLocation();
  return (
    <LocationBoundary state={state}>
      {(l) => (
        <Screen>
          <ScreenHeader
            title="Your next stop."
            subtitle={`${l.name} · ${l.floor}`}
            back
          />
          <CampusMap locations={[l]} selectedId={l.id} onSelect={() => {}} />
          <DemoNote text="Route preview · illustrative campus map" />
          <Card>
            <Copy variant="heading">Walking routes are coming later</Copy>
            <Copy muted>
              Head toward {l.building}, then find {l.floor.toLowerCase()}. This
              demo does not provide turn-by-turn directions or use your current
              location.
            </Copy>
            <Button
              label="Explore campus map"
              onPress={() => router.push("/(tabs)/map")}
            />
          </Card>
        </Screen>
      )}
    </LocationBoundary>
  );
}
