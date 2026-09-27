import AsyncStorage from "@react-native-async-storage/async-storage";
import { Session } from "@supabase/supabase-js";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  PropsWithChildren,
} from "react";
import { AppState, Platform } from "react-native";
import * as WebBrowser from "expo-web-browser";
import { makeRedirectUri } from "expo-auth-session";
import { requireAuth, supabase } from "../services/auth/supabase";
import { setAuthBridge } from "../services/auth/bridge";
import { ApiError } from "../services/api/client";
import { authError } from "../services/auth/errors";
WebBrowser.maybeCompleteAuthSession();
const INTRO = "studyspot:intro:v1";
export const callbackUrl = () =>
  makeRedirectUri({ scheme: "studyspot", path: "auth/callback" });
const resetUrl = () => callbackUrl() + "?recovery=1";
function useAuthState() {
  const [session, setSession] = useState<Session | null>(null);
  const current = useRef<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [introComplete, setIntroComplete] = useState(false);
  const [recovery, setRecovery] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const refreshInFlight = useRef<Promise<string | null> | null>(null);
  const callbacks = useRef(new Map<string, Promise<void>>());
  const accept = useCallback((value: Session | null) => {
    current.current = value;
    setSession(value);
  }, []);
  // Split so the mount effect can await the session without a synchronous
  // setState at the top of an effect; `loading`/`error` already start correct.
  // The public `bootstrap` (used by the Retry button) resets both first.
  const load = useCallback(async () => {
    try {
      const intro = await AsyncStorage.getItem(INTRO);
      setIntroComplete(intro === "true");
      if (supabase) {
        const result = await supabase.auth.getSession();
        if (result.error) throw result.error;
        accept(result.data.session);
      }
    } catch (e) {
      setError(authError(e));
    } finally {
      setLoading(false);
    }
  }, [accept]);
  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError(null);
    await load();
  }, [load]);
  const signOut = useCallback(async () => {
    const { error: failure } = await requireAuth().auth.signOut({
      scope: "local",
    });
    if (failure) throw failure;
    accept(null);
    setRecovery(false);
  }, [accept]);
  useEffect(() => {
    setAuthBridge({
      subject: () => current.current?.user.id ?? null,
      token: async () => {
        const { data, error: failure } = await requireAuth().auth.getSession();
        if (failure)
          throw new ApiError(
            "AUTH_NETWORK",
            "Couldn’t restore your session. Please retry.",
          );
        return data.session?.access_token ?? null;
      },
      refresh: () => {
        if (!refreshInFlight.current) {
          refreshInFlight.current = (async () => {
            const { data, error: failure } =
              await requireAuth().auth.refreshSession();
            if (failure) {
              // Supabase removes genuinely invalid refresh sessions itself. Transport
              // errors retain the session; never equate an outage with invalid identity.
              if (
                failure.status === 400 ||
                failure.status === 401 ||
                failure.status === 403
              )
                return null;
              throw new ApiError(
                "AUTH_NETWORK",
                "Couldn’t refresh your session. Check your connection and retry.",
              );
            }
            return data.session?.access_token ?? null;
          })().finally(() => {
            refreshInFlight.current = null;
          });
        }
        return refreshInFlight.current;
      },
      invalidate: async () => {
        await signOut();
        setError("Your session has expired. Please sign in again.");
      },
    });
    const subscription = supabase?.auth.onAuthStateChange((event, value) => {
      accept(value);
      if (event === "PASSWORD_RECOVERY") setRecovery(true);
      if (event === "SIGNED_OUT") setRecovery(false);
    });
    // Session restore on mount has to run here: it's a one-time read of an
    // external system (SecureStore/AsyncStorage + Supabase), not a response to
    // a state change, so there is no non-effect place to trigger it from.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    const updateRefresh = (state: string) => {
      if (state === "active") supabase?.auth.startAutoRefresh();
      else supabase?.auth.stopAutoRefresh();
    };
    if (Platform.OS !== "web") updateRefresh(AppState.currentState);
    const appState = AppState.addEventListener("change", updateRefresh);
    return () => {
      subscription?.data.subscription.unsubscribe();
      appState.remove();
      supabase?.auth.stopAutoRefresh();
    };
  }, [accept, load, signOut]);
  const completeCallback = useCallback(
    (url: string) => {
      const parsed = new URL(url);
      if (parsed.searchParams.has("error"))
        return Promise.reject(new Error("OAUTH_FAILED"));
      const code = parsed.searchParams.get("code");
      if (!code) return Promise.reject(new Error("MISSING_CODE"));
      const existing = callbacks.current.get(code);
      if (existing) return existing;
      const promise = (async () => {
        if (parsed.searchParams.get("recovery") === "1") setRecovery(true);
        const { data, error: failure } =
          await requireAuth().auth.exchangeCodeForSession(code);
        if (failure) {
          setRecovery(false);
          throw failure;
        }
        accept(data.session);
      })();
      if (callbacks.current.size > 10) callbacks.current.clear();
      callbacks.current.set(code, promise);
      return promise;
    },
    [accept],
  );
  return {
    session,
    user: session?.user ?? null,
    isAuthenticated: !!session,
    loading,
    introComplete,
    recovery,
    error,
    bootstrap,
    signOut,
    completeCallback,
    finishIntro: async () => {
      await AsyncStorage.setItem(INTRO, "true");
      setIntroComplete(true);
    },
    signIn: async (email: string, password: string) => {
      setError(null);
      const { error: failure } = await requireAuth().auth.signInWithPassword({
        email,
        password,
      });
      if (failure) throw failure;
    },
    signUp: async (email: string, password: string) => {
      const { data, error: failure } = await requireAuth().auth.signUp({
        email,
        password,
        options: { emailRedirectTo: callbackUrl() },
      });
      if (failure) throw failure;
      return !!data.session;
    },
    oauth: async (provider: "google") => {
      const redirectTo = callbackUrl();
      const { data, error: failure } = await requireAuth().auth.signInWithOAuth(
        { provider, options: { redirectTo, skipBrowserRedirect: true } },
      );
      if (failure) throw failure;
      if (Platform.OS === "web") {
        window.location.assign(data.url);
        return;
      }
      const result = await WebBrowser.openAuthSessionAsync(
        data.url,
        redirectTo,
      );
      if (result.type !== "success") throw new Error("OAUTH_CANCELLED");
      await completeCallback(result.url);
    },
    forgotPassword: async (email: string) => {
      const { error: failure } = await requireAuth().auth.resetPasswordForEmail(
        email,
        { redirectTo: resetUrl() },
      );
      if (failure) throw failure;
    },
    resetPassword: async (password: string) => {
      const { error: failure } = await requireAuth().auth.updateUser({
        password,
      });
      if (failure) throw failure;
      setRecovery(false);
    },
  };
}
const Context = createContext<ReturnType<typeof useAuthState> | null>(null);
export function AuthProvider({ children }: PropsWithChildren) {
  return <Context.Provider value={useAuthState()}>{children}</Context.Provider>;
}
export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}
