import AsyncStorage from "@react-native-async-storage/async-storage";
import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
} from "react";
import { CrowdReport, UserPreferences, User } from "../types";
import { defaultPreferences, userService } from "../services/userService";
import { favoriteService } from "../services/favoriteService";
import { errorMessage } from "../services/api/client";
interface State {
  user: User;
  ready: boolean;
  signedIn: boolean;
  preferences: UserPreferences;
  favorites: string[];
  recent: string[];
  checkIn: string | null;
  reports: CrowdReport[];
  notifications: boolean;
  storageError: string | null;
  mutationError: string | null;
  pendingFavorites: string[];
}
interface Actions {
  login: () => Promise<void>;
  logout: () => void;
  savePreferences: (p: UserPreferences) => Promise<boolean>;
  toggleFavorite: (id: string) => Promise<void>;
  visit: (id: string) => void;
  setCheckIn: (id: string | null) => void;
  addReport: (r: CrowdReport) => void;
  setNotifications: (v: boolean) => void;
  clearMutationError: () => void;
}
const initial: State = {
  user: { id: "", name: "", email: "", preferences: defaultPreferences },
  ready: false,
  signedIn: false,
  preferences: defaultPreferences,
  favorites: [],
  recent: [],
  checkIn: null,
  reports: [],
  notifications: true,
  storageError: null,
  mutationError: null,
  pendingFavorites: [],
};
const Context = createContext<(State & Actions) | null>(null);
const KEY = "studyspot:device:v2";
export function AppProvider({ children }: React.PropsWithChildren) {
  const [state, set] = useState(initial);
  const inFlight = useRef(new Set<string>());
  const session = useRef(0);
  const saving = useRef(false);
  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((raw) => {
        if (raw) {
          const value: unknown = JSON.parse(raw);
          if (
            value &&
            typeof value === "object" &&
            "notifications" in value &&
            typeof value.notifications === "boolean"
          ) {
            const notifications = value.notifications;
            set((s) => ({ ...s, notifications }));
          }
        }
      })
      .catch(() =>
        set((s) => ({
          ...s,
          storageError: "Device settings could not be read.",
        })),
      )
      .finally(() => set((s) => ({ ...s, ready: true })));
  }, []);
  useEffect(() => {
    if (state.ready)
      AsyncStorage.setItem(
        KEY,
        JSON.stringify({ notifications: state.notifications }),
      ).catch(() =>
        set((s) =>
          s.storageError
            ? s
            : {
                ...s,
                storageError:
                  "Device notification settings could not be saved.",
              },
        ),
      );
  }, [state.ready, state.notifications]);
  const login = async () => {
    const generation = ++session.current;
    const dto = await userService.getDevelopmentUser();
    const [preferences, favorites] = await Promise.all([
      userService.getPreferences(dto.id),
      favoriteService.getFavorites(dto.id),
    ]);
    if (generation !== session.current) return;
    set((s) => ({
      ...s,
      signedIn: true,
      user: {
        id: dto.id,
        name: dto.display_name,
        email: dto.email,
        preferences,
      },
      preferences,
      favorites,
      mutationError: null,
    }));
  };
  const savePreferences = async (preferences: UserPreferences) => {
    if (saving.current || !state.signedIn) return false;
    saving.current = true;
    const generation = session.current;
    try {
      const saved = await userService.savePreferences(
        state.user.id,
        preferences,
      );
      if (generation !== session.current) return false;
      set((s) => ({ ...s, preferences: saved, mutationError: null }));
      return true;
    } catch (error) {
      if (generation === session.current)
        set((s) => ({ ...s, mutationError: errorMessage(error) }));
      return false;
    } finally {
      saving.current = false;
    }
  };
  const toggleFavorite = async (id: string) => {
    if (inFlight.current.has(id) || !state.signedIn) return;
    inFlight.current.add(id);
    const generation = session.current;
    const wasFavorite = state.favorites.includes(id);
    set((s) => ({
      ...s,
      mutationError: null,
      pendingFavorites: [...s.pendingFavorites, id],
      favorites: wasFavorite
        ? s.favorites.filter((x) => x !== id)
        : [...s.favorites, id],
    }));
    try {
      if (wasFavorite) await favoriteService.remove(state.user.id, id);
      else await favoriteService.add(state.user.id, id);
    } catch (error) {
      if (generation === session.current)
        set((s) => ({
          ...s,
          mutationError: `Favorite not saved. ${errorMessage(error)}`,
          favorites: wasFavorite
            ? [...s.favorites.filter((x) => x !== id), id]
            : s.favorites.filter((x) => x !== id),
        }));
    } finally {
      inFlight.current.delete(id);
      if (generation === session.current)
        set((s) => ({
          ...s,
          pendingFavorites: s.pendingFavorites.filter((x) => x !== id),
        }));
    }
  };
  const visit = useCallback(
    (id: string) =>
      set((s) =>
        s.recent[0] === id
          ? s
          : {
              ...s,
              recent: [id, ...s.recent.filter((x) => x !== id)].slice(0, 10),
            },
      ),
    [],
  );
  return (
    <Context.Provider
      value={{
        ...state,
        user: { ...state.user, preferences: state.preferences },
        login,
        savePreferences,
        toggleFavorite,
        visit,
        logout: () => {
          session.current++;
          set((s) => ({
            ...initial,
            ready: true,
            notifications: s.notifications,
          }));
        },
        setCheckIn: (checkIn) => set((s) => ({ ...s, checkIn })),
        addReport: (report) =>
          set((s) => ({ ...s, reports: [...s.reports, report] })),
        setNotifications: (notifications) =>
          set((s) => ({ ...s, notifications })),
        clearMutationError: () => set((s) => ({ ...s, mutationError: null })),
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useApp() {
  const value = useContext(Context);
  if (!value) throw new Error("AppProvider is required");
  return value;
}
