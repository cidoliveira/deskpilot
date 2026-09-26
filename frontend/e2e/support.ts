import { expect, type APIRequestContext, type Page } from "@playwright/test";

const API = process.env.E2E_API_URL ?? "http://localhost:8000/api/v1";
export const PASSWORD = "E2e-Str0ng-password";

export interface Account {
  id: number;
  name: string;
  email: string;
}

let sequence = 0;
const unique = (prefix: string) => `${prefix}-${Date.now()}-${++sequence}@example.com`;

async function apiLogin(request: APIRequestContext, email: string, password: string) {
  const response = await request.post(`${API}/auth/login`, { form: { username: email, password } });
  expect(response.ok(), `login as ${email}`).toBeTruthy();
  return ((await response.json()) as { access_token: string }).access_token;
}

/** Creates a fresh account (through the admin API) so every test starts from zero. */
export async function createAccount(
  request: APIRequestContext,
  role: "USER" | "TECHNICIAN",
  name: string,
): Promise<Account> {
  const adminEmail = process.env.FIRST_ADMIN_EMAIL;
  const adminPassword = process.env.FIRST_ADMIN_PASSWORD;
  if (!adminEmail || !adminPassword) throw new Error("Set FIRST_ADMIN_EMAIL/PASSWORD for e2e");

  const token = await apiLogin(request, adminEmail, adminPassword);
  const response = await request.post(`${API}/users`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { name, email: unique(role.toLowerCase()), password: PASSWORD, role },
  });
  expect(response.status(), "create account").toBe(201);
  return (await response.json()) as Account;
}

export async function signIn(page: Page, account: Pick<Account, "email">) {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(account.email);
  await page.getByLabel("Senha").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

export async function signOut(page: Page) {
  await page.getByRole("button", { name: "Sair" }).first().click();
  await expect(page).toHaveURL(/\/login/);
}
