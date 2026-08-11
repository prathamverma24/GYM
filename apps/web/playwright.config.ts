import { defineConfig } from "@playwright/test";
import path from "node:path";

const apiDirectory = path.resolve(__dirname, "../api");
const webDirectory = path.resolve(__dirname);

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  fullyParallel: false,
  reporter: "list",
  use: {
    baseURL: process.env.WEB_URL ?? "http://localhost:3000",
    channel: process.env.PLAYWRIGHT_CHANNEL ?? (process.platform === "win32" ? "chrome" : undefined),
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000",
      cwd: apiDirectory,
      url: "http://localhost:8000/health",
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      cwd: webDirectory,
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
