import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { createAccount, signIn, signOut } from "./support";

/** Automated WCAG 2.x A/AA check. It does not replace manual testing, but catches the
 *  common failures: contrast, missing labels, invalid ARIA, landmark problems. */
async function expectNoViolations(page: Page, screen: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const summary = results.violations.map(
    (violation) =>
      `${violation.id} (${violation.impact}): ${violation.help}\n    ${violation.nodes
        .slice(0, 3)
        .map((node) => node.target.join(" "))
        .join("\n    ")}`,
  );
  expect(summary, `accessibility violations on ${screen}`).toEqual([]);
}

test("main screens have no detectable accessibility violations", async ({ page, request }) => {
  const suffix = Date.now();
  const user = await createAccount(request, "USER", `Acessível ${suffix}`);
  const tech = await createAccount(request, "TECHNICIAN", `Técnica ${suffix}`);

  await page.goto("/login");
  await expectNoViolations(page, "login");

  await signIn(page, user);
  await page.goto("/tickets/new");
  await expectNoViolations(page, "new ticket");
  await page.getByLabel("Resumo do problema").fill(`Scanner sem driver ${suffix}`);
  await page.getByLabel("Categoria").selectOption({ label: "Hardware" });
  await page.getByLabel("Descrição").fill("O scanner não aparece depois da atualização.");
  await page.getByRole("button", { name: "Abrir chamado" }).click();
  await expect(page.getByRole("heading", { name: /Scanner sem driver/ })).toBeVisible();
  const ticketUrl = page.url();
  await expectNoViolations(page, "ticket detail (user)");
  await page.goto("/tickets");
  await expect(page.getByRole("table")).toBeVisible();
  await expectNoViolations(page, "my tickets");
  await signOut(page);

  await signIn(page, tech);
  await page.goto("/queue?view=available");
  await expect(page.getByRole("table")).toBeVisible();
  await expectNoViolations(page, "queue");
  await page.goto(ticketUrl);
  await expect(page.getByRole("button", { name: "Assumir chamado" })).toBeVisible();
  await expectNoViolations(page, "ticket detail (technician)");
});

test("admin screens have no detectable accessibility violations", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(process.env.FIRST_ADMIN_EMAIL ?? "");
  await page.getByLabel("Senha").fill(process.env.FIRST_ADMIN_PASSWORD ?? "");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("heading", { name: "Painel do service desk" })).toBeVisible();
  await expectNoViolations(page, "dashboard");

  await page.goto("/admin");
  await expect(page.getByRole("list", { name: "Usuários" })).toBeVisible();
  await expectNoViolations(page, "admin users");
  await page.goto("/admin?tab=categories");
  await expect(page.getByText("Nova categoria")).toBeVisible();
  await expectNoViolations(page, "admin categories");
});

test("keyboard users can skip the menu", async ({ page, request }) => {
  const user = await createAccount(request, "USER", `Teclado ${Date.now()}`);
  await signIn(page, user);
  await page.goto("/tickets");
  await expect(page.getByRole("heading", { name: "Meus chamados" })).toBeVisible();

  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Pular para o conteúdo" });
  await expect(skip).toBeFocused();
  await expect(skip).toBeVisible();

  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
});

test("every screen fits a phone without sideways scrolling", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(process.env.FIRST_ADMIN_EMAIL ?? "");
  await page.getByLabel("Senha").fill(process.env.FIRST_ADMIN_PASSWORD ?? "");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("heading", { name: "Painel do service desk" })).toBeVisible();

  for (const path of [
    "/dashboard",
    "/queue?view=all",
    "/tickets",
    "/tickets/new",
    "/admin",
    "/admin?tab=categories",
  ]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow, `${path} is ${overflow}px wider than the phone`).toBeLessThanOrEqual(0);
  }
});
