import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { AppState } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { deviceLocationService } from "../services/location/deviceLocationService";
import {
  createLocationController,
  LocationState,
  LOCATION_TTL,
} from "../services/location/locationController";
import { routingService } from "../services/location/routingService";
import { useAuth } from "./AuthProvider";
interface State extends LocationState {
  dismissed: boolean;
  requestPermission(): Promise<void>;
  refreshLocation(): Promise<void>;
  dismiss(): void;
}
const Context = createContext<State | null>(null);
export function LocationProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();
  return (
    <LocationSession key={auth.session?.user.id ?? "anonymous"}>
      {children}
    </LocationSession>
  );
}
function LocationSession({ children }: { children: ReactNode }) {
  const [state, setState] = useState<LocationState>({
    permissionStatus: "unknown",
    coordinates: null,
    isLoading: false,
    error: null,
  });
  const [controller] = useState(() =>
    createLocationController(deviceLocationService, setState),
  );
  const [dismissed, setDismissed] = useState(true);
  useEffect(() => {
    let active = true;
    void AsyncStorage.getItem("studyspot.location.dismissed")
      .then((value) => {
        if (active) setDismissed(value === "1");
      })
      .catch(() => {});
    const sub = AppState.addEventListener("change", (status) => {
      if (status === "background") {
        controller.clear();
        routingService.clear();
      }
    });
    return () => {
      active = false;
      controller.clear();
      routingService.clear();
      sub.remove();
    };
  }, [controller]);
  function dismiss() {
    setDismissed(true);
    void AsyncStorage.setItem("studyspot.location.dismissed", "1").catch(
      () => {},
    );
  }
  useEffect(() => {
    if (!state.coordinates) return;
    const timer = setTimeout(
      () => {
        controller.clear();
        routingService.clear();
      },
      Math.max(0, LOCATION_TTL - (Date.now() - state.coordinates.timestamp)),
    );
    return () => clearTimeout(timer);
  }, [state.coordinates, controller]);
  return (
    <Context.Provider
      value={{
        ...state,
        dismissed,
        requestPermission: async () => {
          dismiss();
          await controller.acquire(true);
        },
        refreshLocation: () => controller.acquire(false),
        dismiss,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useDeviceLocation() {
  const context = useContext(Context);
  if (!context) throw new Error("LocationProvider missing");
  return context;
}
