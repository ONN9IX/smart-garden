/** Browser integration against real Backend + PostgreSQL (see CI integration job). */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  use: {
    baseURL: "http://localhost:3000",
    trace: "off",
    screenshot: "off",
    video: "off",
  },
});
