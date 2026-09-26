import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8081",
    viewport: { width: 390, height: 844 },
    launchOptions: { channel: "chrome" },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "cd ../backend && .venv/bin/python -m tests.serve_e2e",
      url: "http://127.0.0.1:8002/api/v1/health",
      reuseExistingServer: false,
      timeout: 120000,
    },
    {
      command: "npx expo start --web --port 8081",
      url: "http://127.0.0.1:8081",
      reuseExistingServer: false,
      timeout: 120000,
      env: { EXPO_PUBLIC_API_URL: "http://127.0.0.1:8002/api/v1" },
    },
  ],
});
