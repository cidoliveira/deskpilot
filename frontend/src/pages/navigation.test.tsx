import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { admin, ana, carla, metrics, page } from "../test/fixtures";
import { renderApp } from "../test/renderApp";

const emptyList = { "GET /tickets": page([]), "GET /categories": [] };

describe("navigation by role", () => {
  it("sends visitors without a session to the login screen", async () => {
    const { router } = renderApp("/queue", {});

    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });

  it.each([
    [ana, "/tickets", "Meus chamados"],
    [carla, "/queue", "Fila de atendimento"],
    [admin, "/dashboard", "Painel do service desk"],
  ])("lands each role on its own start page (%#)", async (user, path, heading) => {
    const { router } = renderApp("/", {
      user,
      api: { ...emptyList, "GET /dashboard/metrics": metrics },
    });

    expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(path);
  });

  it("offers each role only its own menu", async () => {
    renderApp("/tickets", { user: ana, api: emptyList });

    expect(await screen.findByRole("link", { name: "Meus chamados" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Fila de atendimento" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Administração" })).not.toBeInTheDocument();
  });

  it("sends a user who types a staff address back to the start", async () => {
    const { router } = renderApp("/admin", { user: ana, api: emptyList });

    expect(await screen.findByRole("heading", { name: "Meus chamados" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/tickets");
  });

  it("explains unknown addresses", async () => {
    renderApp("/nao-existe", { user: ana, api: emptyList });

    expect(await screen.findByText("Página não encontrada")).toBeInTheDocument();
  });
});
