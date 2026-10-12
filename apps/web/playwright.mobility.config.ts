import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: [
    "mobility-offline.spec.ts",
    "mobility-open-map.spec.ts",
    "map-ui-primitives.spec.ts",
    "mobility-map-reuse.spec.ts",
  ],
  outputDir: "../../output/playwright/mobility-tests",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3031",
    trace: "retain-on-failure",
    timezoneId: "Asia/Ho_Chi_Minh",
    viewport: { width: 1440, height: 960 },
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "node node_modules/next/dist/bin/next dev -p 3031",
    url: "http://localhost:3031",
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      MOBILITY_ENABLED: process.env.P2UI_WEB_MOBILITY_ENABLED ?? "true",
      API_INTERNAL_URL: "http://127.0.0.1:9",
      MOBILITY_TILES_ENABLED: process.env.P2UI_WEB_TILES_ENABLED ?? "false",
      MOBILITY_TILE_URL: process.env.P2UI_WEB_TILE_URL ?? "",
      MOBILITY_TILE_ATTRIBUTION:
        process.env.P2UI_WEB_TILE_ATTRIBUTION ?? "",
      MOBILITY_ALLOWED_TILE_ORIGIN:
        process.env.P2UI_WEB_ALLOWED_TILE_ORIGIN ?? "",
      GOOGLE_LIVE_ENABLED: "true",
      NEXT_TELEMETRY_DISABLED: "1",
    },
  },
});
