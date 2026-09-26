// Regenerates the README screenshots in docs/screenshots.
//
// Needs the API with the demo data (python -m app.scripts.seed_demo) and the dev server:
//   npm run dev        # in another terminal
//   npm run screenshots
// Credentials come from the repository .env (FIRST_ADMIN_*, DEMO_PASSWORD).
import { chromium } from "@playwright/test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const BASE = process.env.SCREENSHOTS_BASE_URL ?? "http://localhost:5173";
const OUT = new URL("../../docs/screenshots/", import.meta.url);

const env = Object.fromEntries(
  readFileSync(new URL("../../.env", import.meta.url), "utf8")
    .split(/\r?\n/)
    .map((line) => line.match(/^([A-Z0-9_]+)=(.*)$/))
    .filter(Boolean)
    .map((match) => [match[1], match[2]]),
);

const DESKTOP = { width: 1366, height: 860 };
const PHONE = { width: 390, height: 844 };
const browser = await chromium.launch();

async function openSession(viewport, account) {
  const context = await browser.newContext({
    viewport,
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
  });
  const page = await context.newPage();
  await page.goto(`${BASE}/login`);
  if (account) {
    await page.getByLabel("E-mail").fill(account.email);
    await page.getByLabel("Senha").fill(account.password);
    await page.getByRole("button", { name: "Entrar" }).click();
    await page.waitForURL((url) => !url.pathname.startsWith("/login"));
  }
  return page;
}

async function capture(page, path, name, fullPage = true) {
  await page.goto(`${BASE}${path}`);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(700); // let the SLA bars finish their transition
  await page.screenshot({ path: fileURLToPath(new URL(`${name}.png`, OUT)), fullPage });
  console.log(`  ${name}.png`);
}

const anonymous = await openSession(DESKTOP);
await capture(anonymous, "/login", "login", false);

const admin = await openSession(DESKTOP, {
  email: env.FIRST_ADMIN_EMAIL,
  password: env.FIRST_ADMIN_PASSWORD,
});
await capture(admin, "/dashboard", "dashboard");
await capture(admin, "/queue?view=all", "queue");
await capture(admin, "/tickets/2", "ticket");
await capture(admin, "/tickets/new", "new-ticket", false);

const user = await openSession(PHONE, { email: "ana@deskpilot.dev", password: env.DEMO_PASSWORD });
await capture(user, "/tickets/1", "mobile", false);

await browser.close();
