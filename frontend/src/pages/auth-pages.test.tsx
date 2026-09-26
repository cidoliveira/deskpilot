import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ana, page } from "../test/fixtures";
import { renderApp, reply } from "../test/renderApp";

const TOKEN = { access_token: "t", token_type: "bearer", expires_in: 3600 };

describe("LoginPage", () => {
  it("signs in and opens the start page of the role", async () => {
    const user = userEvent.setup();
    const { api, router } = renderApp("/login", {
      api: {
        "POST /auth/login": TOKEN,
        "GET /auth/me": ana,
        "GET /tickets": page([]),
        "GET /categories": [],
      },
    });

    await user.type(await screen.findByLabelText("E-mail"), "ana@example.com");
    await user.type(screen.getByLabelText("Senha"), "Str0ng-password");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("heading", { name: "Meus chamados" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/tickets");
    expect(api.calls("POST /auth/login")[0].body).toEqual({
      username: "ana@example.com",
      password: "Str0ng-password",
    });
  });

  it("shows the reason when the login is refused", async () => {
    const user = userEvent.setup();
    renderApp("/login", {
      api: {
        "POST /auth/login": reply(401, { error: "invalid_credentials", message: "Incorrect" }),
      },
    });

    await user.type(await screen.findByLabelText("E-mail"), "ana@example.com");
    await user.type(screen.getByLabelText("Senha"), "wrong");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou senha incorretos.");
  });

  it("returns to the page the visitor asked for after signing in", async () => {
    const user = userEvent.setup();
    const { router } = renderApp("/tickets/new", {
      api: { "POST /auth/login": TOKEN, "GET /auth/me": ana, "GET /categories": [] },
    });

    await user.type(await screen.findByLabelText("E-mail"), "ana@example.com");
    await user.type(screen.getByLabelText("Senha"), "Str0ng-password");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("heading", { name: "Abrir chamado" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/tickets/new");
  });
});

describe("RegisterPage", () => {
  it("shows the API's validation errors next to each field, in PT-BR", async () => {
    const user = userEvent.setup();
    renderApp("/register", {
      api: {
        "POST /auth/register": reply(422, {
          error: "validation_error",
          message: "Invalid request",
          details: [
            { field: "password", message: "x", type: "string_too_short", ctx: { min_length: 8 } },
          ],
        }),
      },
    });

    await user.type(await screen.findByLabelText("Nome"), "Ana");
    await user.click(screen.getByRole("button", { name: "Criar conta" }));

    expect(await screen.findByText("Use pelo menos 8 caracteres.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument(); // no generic banner
  });

  it("creates the account, signs in and opens the new ticket form", async () => {
    const user = userEvent.setup();
    const { api, router } = renderApp("/register", {
      api: {
        "POST /auth/register": reply(201, ana),
        "POST /auth/login": TOKEN,
        "GET /auth/me": ana,
        "GET /categories": [],
      },
    });

    await user.type(await screen.findByLabelText("Nome"), "Ana Souza");
    await user.type(screen.getByLabelText("E-mail corporativo"), "ana@example.com");
    await user.type(screen.getByLabelText("Senha"), "Str0ng-password");
    await user.click(screen.getByRole("button", { name: "Criar conta" }));

    expect(await screen.findByRole("heading", { name: "Abrir chamado" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/tickets/new");
    expect(api.calls("POST /auth/register")[0].body).toEqual({
      name: "Ana Souza",
      email: "ana@example.com",
      password: "Str0ng-password",
    });
  });
});
