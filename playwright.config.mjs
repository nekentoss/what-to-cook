import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/browser",
  workers: 1,
  use: { baseURL: "http://127.0.0.1:18794", channel: "chrome" },
  webServer: {
    command: "python -m tests.browser.server",
    url: "http://127.0.0.1:18794/docs",
    reuseExistingServer: false,
  },
});
