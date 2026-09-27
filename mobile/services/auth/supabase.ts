import "react-native-url-polyfill/auto";
import { createClient, processLock } from "@supabase/supabase-js";
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import { createSecureStorage } from "./secureStorage";
const url = process.env.EXPO_PUBLIC_SUPABASE_URL;
const key = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;
export const authConfigured = Boolean(url && key);
// No placeholder identity when unconfigured. Public catalog remains usable by API clients.
export const supabase =
  url && key
    ? createClient(url, key, {
        auth: {
          storage:
            Platform.OS === "web"
              ? undefined
              : createSecureStorage(SecureStore),
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: false,
          flowType: "pkce",
          lock: processLock,
        },
      })
    : null;
export function requireAuth() {
  if (!supabase) throw new Error("AUTH_CONFIGURATION");
  return supabase;
}
