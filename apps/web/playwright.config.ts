import { defineConfig, devices } from "@playwright/test";

// ponytail: web+api chạy sẵn trong docker, không dùng webServer. Đổi baseURL nếu chạy ngoài docker.
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
