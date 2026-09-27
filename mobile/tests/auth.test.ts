import test from "node:test";
import assert from "node:assert/strict";
import { accountRoute } from "../services/auth/routing";
import {
  createSecureStorage,
  SecureEngine,
} from "../services/auth/secureStorage";

test("auth routing separates device intro from account onboarding", () => {
  assert.equal(accountRoute(false, false, false), "/(auth)/onboarding");
  assert.equal(accountRoute(false, true, false), "/(auth)/login");
  assert.equal(accountRoute(true, true, false), "/(auth)/preferences");
  assert.equal(accountRoute(true, false, true), "/(tabs)");
});

test("secure session storage chunks, restores, replaces, and removes tokens", async () => {
  const values = new Map<string, string>();
  const engine: SecureEngine = {
    getItemAsync: async (key) => values.get(key) ?? null,
    setItemAsync: async (key, value) => {
      values.set(key, value);
    },
    deleteItemAsync: async (key) => {
      values.delete(key);
    },
  };
  const storage = createSecureStorage(engine);
  const first = "token:" + "x".repeat(1400);
  await storage.setItem("session", first);
  assert.equal(await storage.getItem("session"), first);
  assert.ok(values.size > 2);
  await storage.setItem("session", "replacement");
  assert.equal(await storage.getItem("session"), "replacement");
  assert.equal(
    [...values.keys()].filter((key) => key.startsWith("session.")).length,
    1,
  );
  await storage.removeItem("session");
  assert.equal(await storage.getItem("session"), null);
  assert.equal(values.size, 0);
});

test("secure session storage fails closed on an invalid manifest", async () => {
  const engine: SecureEngine = {
    getItemAsync: async () => JSON.stringify(["another-key.1"]),
    setItemAsync: async () => {},
    deleteItemAsync: async () => {},
  };
  await assert.rejects(
    createSecureStorage(engine).getItem("session"),
    /unreadable/,
  );
});
