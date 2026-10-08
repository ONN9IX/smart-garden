/** Browser integration against real Backend + PostgreSQL (see CI integration job). */
import { defineConfig } from "@playwright/test";

const browserName = (process.env.PLAYWRIGHT_BROWSER ?? "chromium") as "chromium" | "firefox" | "webkit";

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  projects: [{ name: browserName, use: { browserName } }],
  use: {
    baseURL: "http://localhost:3000",
    trace: "off",
    screenshot: "off",
    video: "off",
  },
});
