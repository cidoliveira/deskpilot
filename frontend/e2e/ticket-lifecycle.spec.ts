import { expect, test } from "@playwright/test";
import { createAccount, signIn, signOut } from "./support";

test("a ticket goes from opened to closed, with every step on record", async ({
  page,
  request,
}) => {
  const suffix = Date.now();
  const title = `Monitor não liga ${suffix}`;
  const user = await createAccount(request, "USER", `Paula ${suffix}`);
  const tech = await createAccount(request, "TECHNICIAN", `Renato ${suffix}`);

  // 1. The user opens a ticket.
  await signIn(page, user);
  await page.getByRole("link", { name: "Abrir chamado" }).first().click();
  await page.getByLabel("Resumo do problema").fill(title);
  await page.getByLabel("Categoria").selectOption({ label: "Hardware" });
  await page.getByLabel("Prioridade").selectOption({ label: "Alta" });
  await expect(page.getByText("resolução em até 8 h")).toBeVisible();
  await page.getByLabel("Descrição").fill("O monitor externo não liga desde hoje cedo.");
  await page.getByRole("button", { name: "Abrir chamado" }).click();

  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  const ticketUrl = page.url();
  await expect(page.getByText("Aberto", { exact: true })).toBeVisible();
  await expect(page.getByText("No prazo", { exact: true })).toBeVisible();
  await signOut(page);

  // 2. A technician finds it among the available tickets, claims and resolves it.
  await signIn(page, tech);
  await page.getByRole("tab", { name: "Disponíveis" }).click();
  await page.getByRole("searchbox", { name: "Buscar" }).fill(String(suffix));
  await page.getByRole("link", { name: new RegExp(title) }).click();

  await page.getByRole("button", { name: "Assumir chamado" }).click();
  await page.getByRole("button", { name: "Iniciar atendimento" }).click();
  await expect(page.getByText("Em andamento", { exact: true }).first()).toBeVisible();

  await page.getByRole("textbox", { name: "Nova mensagem" }).fill("Trocando o cabo HDMI.");
  await page.getByRole("button", { name: "Enviar mensagem" }).click();
  await expect(page.getByText("Trocando o cabo HDMI.")).toBeVisible();

  await page.getByRole("button", { name: "Resolver" }).click();
  await page.getByLabel("O que resolveu o problema?").fill("Cabo HDMI substituído.");
  await page.getByRole("button", { name: "Marcar como resolvido" }).click();
  await expect(page.getByText("Cabo HDMI substituído.")).toBeVisible();
  await expect(page.getByText("Cumprido", { exact: true })).toBeVisible();
  await signOut(page);

  // 3. The user confirms the solution; the ticket closes and stops accepting messages.
  await signIn(page, user);
  await page.goto(ticketUrl);
  await page.getByRole("button", { name: "Confirmar e fechar" }).click();
  await expect(page.getByText("Fechado", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Chamado encerrado: não recebe novas mensagens.")).toBeVisible();
  await expect(page.getByText("Nenhuma ação disponível para você agora.")).toBeVisible();

  const history = page.locator("ol");
  for (const step of [
    "abriu o chamado",
    "assumiu o chamado",
    "mudou de Aberto para Em andamento",
    "resolveu o chamado",
    "confirmou a solução e fechou o chamado",
  ]) {
    await expect(history.getByText(step)).toBeVisible();
  }
});

test("an answer from the user resumes a ticket waiting for them", async ({ page, request }) => {
  const suffix = Date.now();
  const title = `Senha do ERP expirada ${suffix}`;
  const user = await createAccount(request, "USER", `Lia ${suffix}`);
  const tech = await createAccount(request, "TECHNICIAN", `Otto ${suffix}`);

  await signIn(page, user);
  await page.goto("/tickets/new");
  await page.getByLabel("Resumo do problema").fill(title);
  await page.getByLabel("Categoria").selectOption({ label: "Access" });
  await page.getByLabel("Descrição").fill("O ERP pede troca de senha e recusa a nova.");
  await page.getByRole("button", { name: "Abrir chamado" }).click();
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  const ticketUrl = page.url();
  await signOut(page);

  await signIn(page, tech);
  await page.goto(ticketUrl);
  await page.getByRole("button", { name: "Assumir chamado" }).click();
  await page.getByRole("button", { name: "Iniciar atendimento" }).click();
  await page.getByRole("button", { name: "Aguardar usuário" }).click();
  await expect(page.getByText("Aguardando usuário", { exact: true }).first()).toBeVisible();
  await signOut(page);

  await signIn(page, user);
  await page.goto(ticketUrl);
  await expect(page.getByText("O técnico aguarda a sua resposta.", { exact: false })).toBeVisible();
  await page
    .getByRole("textbox", { name: "Nova mensagem" })
    .fill("A nova senha tem 12 caracteres.");
  await page.getByRole("button", { name: "Enviar mensagem" }).click();

  await expect(page.getByText("Em andamento", { exact: true }).first()).toBeVisible();
});
