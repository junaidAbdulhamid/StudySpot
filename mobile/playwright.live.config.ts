import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

// Runs real tile requests; the regular suite stays independent of tile-provider uptime.
export default defineConfig({
  ...base,
  testIgnore: [],
  testMatch: "**/map-live.spec.ts",
});
