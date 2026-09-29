import { useAuth } from "./AuthProvider";
import AsyncStorage from "@react-native-async-storage/async-storage";
import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
} from "react";
import { UserPreferences, User } from "../types";
import { defaultPreferences, userService } from "../services/userService";
import { favoriteService } from "../services/favoriteService";
import { errorMessage } from "../services/api/client";
interface State {
  user: User;
  ready: boolean;
  signedIn: boolean;
  onboardingCompleted: boolean;
  profileError: string | null;
  preferences: UserPreferences;
  favorites: string[];
  recent: string[];
  notifications: boolean;
  storageError: string | null;
  mutationError: string | null;
  pendingFavorites: string[];
}
interface Actions {
  reloadProfile: () => Promise<void>;
  updateProfile: (name: string) => Promise<boolean>;
  logout: () => Promise<void>;
  savePreferences: (p: UserPreferences) => Promise<boolean>;
  toggleFavorite: (id: string) => Promise<void>;
  visit: (id: string) => void;
  setNotifications: (v: boolean) => void;
  clearMutationError: () => void;
}
const initial: State = {
  user: { id: "", name: "", email: "", preferences: defaultPreferences },
  ready: false,
  signedIn: false,
  onboardingCompleted: false,
  profileError: null,
  preferences: defaultPreferences,
  favorites: [],
  recent: [],
  notifications: true,
  storageError: null,
  mutationError: null,
  pendingFavorites: [],
};
const Context = createContext<(State & Actions) | null>(null);
const KEY = "studyspot:device:v2";
export function AppProvider({ children }: React.PropsWithChildren) {
  const auth = useAuth();
  return (
    <AccountStore key={auth.user?.id ?? "signed-out"}>{children}</AccountStore>
  );
}
function AccountStore({ children }: React.PropsWithChildren) {
  const auth = useAuth();
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
  const reloadProfile = useCallback(async () => {
    set((s) => ({ ...s, profileError: null, ready: false }));
    try {
      const generation = ++session.current;
      const dto = await userService.getMe();
      const [preferences, favorites] = await Promise.all([
        userService.getPreferences(),
        favoriteService.getFavorites(),
      ]);
      if (generation !== session.current) return;
      set((s) => ({
        ...s,
        signedIn: true,
        ready: true,
        onboardingCompleted: dto.onboarding_completed,
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
    } catch (error) {
      set((s) => ({ ...s, ready: true, profileError: errorMessage(error) }));
    }
  }, []);
  useEffect(() => {
    if (auth.user?.id) void reloadProfile();
    return () => {
      // Invalidate requests from this exact account store when its keyed provider unmounts.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      session.current++;
    };
  }, [auth.user?.id, reloadProfile]);
  const updateProfile = async (name: string) => {
    const generation = session.current;
    try {
      const dto = await userService.updateProfile(name);
      if (generation !== session.current) return false;
      set((s) => ({
        ...s,
        user: { ...s.user, name: dto.display_name },
        mutationError: null,
      }));
      return true;
    } catch (error) {
      if (generation === session.current)
        set((s) => ({ ...s, mutationError: errorMessage(error) }));
      return false;
    }
  };
  const savePreferences = async (preferences: UserPreferences) => {
    if (saving.current || !state.signedIn) return false;
    saving.current = true;
    const generation = session.current;
    try {
      const saved = await userService.savePreferences(preferences);
      if (generation !== session.current) return false;
      set((s) => ({
        ...s,
        preferences: saved,
        onboardingCompleted: true,
        mutationError: null,
      }));
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
      if (wasFavorite) await favoriteService.remove(id);
      else await favoriteService.add(id);
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
        reloadProfile,
        updateProfile,
        savePreferences,
        toggleFavorite,
        visit,
        logout: auth.signOut,
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
