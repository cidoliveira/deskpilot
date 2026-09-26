import { defineConfig, devices } from "@playwright/test";
import { existsSync, readFileSync } from "node:fs";

/**
 * End-to-end tests against the real stack: browser -> Vite -> FastAPI -> PostgreSQL.
 * The API must be running (http://localhost:8000). The tests create their own users
 * through the API, logging in with the first admin from FIRST_ADMIN_* (read from the
 * environment, or from the repository .env when running locally).
 */
function loadRootEnv() {
  const file = new URL("../.env", import.meta.url);
  if (!existsSync(file)) return;
  for (const line of readFileSync(file, "utf8").split(/\r?\n/)) {
    const match = line.match(/^([A-Z0-9_]+)=(.*)$/);
    if (match && process.env[match[1]] === undefined) process.env[match[1]] = match[2];
  }
}
loadRootEnv();

const CI = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./e2e",
  // One shared database: run the flows one after another.
  workers: 1,
  retries: CI ? 1 : 0,
  reporter: CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://localhost:5173",
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev -- --port 5173 --strictPort",
    url: "http://localhost:5173",
    reuseExistingServer: !CI,
  },
});
