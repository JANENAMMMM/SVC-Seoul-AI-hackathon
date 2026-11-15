import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  workers: 1,
  use: { baseURL: "http://127.0.0.1:8131", channel: "msedge", headless: true },
  reporter: "list",
  outputDir: "test-results",
});
