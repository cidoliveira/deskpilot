import { expect, test } from "@playwright/test";
import { createAccount, signIn } from "./support";

test("users only reach their own tickets and screens", async ({ page, request }) => {
  const suffix = Date.now();
  const owner = await createAccount(request, "USER", `Dono ${suffix}`);
  const stranger = await createAccount(request, "USER", `Curioso ${suffix}`);

  await signIn(page, owner);
  await page.goto("/tickets/new");
  await page.getByLabel("Resumo do problema").fill(`Teclado com teclas falhando ${suffix}`);
  await page.getByLabel("Categoria").selectOption({ label: "Hardware" });
  await page.getByLabel("Descrição").fill("As teclas A e S falham de vez em quando.");
  await page.getByRole("button", { name: "Abrir chamado" }).click();
  await expect(page.getByRole("heading", { name: /Teclado com teclas/ })).toBeVisible();
  const ticketUrl = page.url();

  // Another user opening the same link gets "not found", not the ticket.
  await page.evaluate(() => localStorage.clear());
  await signIn(page, stranger);
  await page.goto(ticketUrl);
  await expect(page.getByText("Chamado não encontrado")).toBeVisible();

  // Staff screens are not offered, and typing their address leads back home.
  await expect(page.getByRole("link", { name: "Fila de atendimento" })).toHaveCount(0);
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/tickets$/);
  await expect(page.getByRole("heading", { name: "Meus chamados" })).toBeVisible();
});

test("wrong credentials are explained in the interface language", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill("ninguem@example.com");
  await page.getByLabel("Senha").fill("senha-errada");
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(page.getByRole("alert")).toHaveText("E-mail ou senha incorretos.");
});
