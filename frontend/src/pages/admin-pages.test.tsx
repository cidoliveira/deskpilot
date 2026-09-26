import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { admin, ana, carla, categories, metrics, page } from "../test/fixtures";
import { renderApp } from "../test/renderApp";

describe("DashboardPage", () => {
  it("leads with what needs action: overdue tickets and the SLA of the backlog", async () => {
    renderApp("/dashboard", { user: admin, api: { "GET /dashboard/metrics": metrics } });

    const alert = await screen.findByRole("link", { name: /já passou do prazo/ });
    expect(alert).toHaveAttribute("href", expect.stringContaining("sla_status=BREACHED"));
    // 5 open tickets: 1 overdue, 1 at risk, 3 on track.
    expect(screen.getByRole("img", { name: "No prazo: 3, Em risco: 1, Fora do prazo: 1" }));
    expect(screen.getByText("67%")).toBeInTheDocument();
    expect(screen.getByText("6 h")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: carla.name })).toBeInTheDocument();
  });

  it("drops the alert when nothing is overdue", async () => {
    renderApp("/dashboard", {
      user: admin,
      api: { "GET /dashboard/metrics": { ...metrics, sla: { ...metrics.sla, breached_open: 0 } } },
    });

    await screen.findByText("Situação do SLA · chamados em aberto");
    expect(screen.queryByText(/já passou do prazo/)).not.toBeInTheDocument();
  });
});

describe("AdminPage", () => {
  const users = page([admin, ana, carla]);

  it("lists users and locks the admin's own row", async () => {
    renderApp("/admin", { user: admin, api: { "GET /users": users } });

    const list = await screen.findByRole("list", { name: "Usuários" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByLabelText(`Perfil de ${admin.name}`)).toBeDisabled();
    expect(screen.getByLabelText(`Perfil de ${ana.name}`)).toBeEnabled();
  });

  it("changes a role and deactivates an account", async () => {
    const user = userEvent.setup();
    const { api } = renderApp("/admin", {
      user: admin,
      api: {
        "GET /users": users,
        [`PATCH /users/${ana.id}`]: { ...ana, role: "TECHNICIAN" },
      },
    });

    await user.selectOptions(await screen.findByLabelText(`Perfil de ${ana.name}`), "TECHNICIAN");
    const anaRow = screen.getByText(ana.email).closest("li")!;
    await user.click(within(anaRow).getByRole("button", { name: "Desativar" }));

    await waitFor(() =>
      expect(api.calls(`PATCH /users/${ana.id}`).map((call) => call.body)).toEqual([
        { role: "TECHNICIAN" },
        { is_active: false },
      ]),
    );
  });

  it("creates a technician account", async () => {
    const user = userEvent.setup();
    const { api } = renderApp("/admin", {
      user: admin,
      api: { "GET /users": users, "POST /users": { status: 201, body: carla } },
    });

    await user.click(await screen.findByRole("button", { name: "Novo usuário" }));
    await user.type(screen.getByLabelText("Nome"), "Diego Rocha");
    await user.type(screen.getByLabelText("E-mail"), "diego@example.com");
    await user.type(screen.getByLabelText("Senha inicial"), "Str0ng-password");
    await user.click(screen.getByRole("button", { name: "Criar usuário" }));

    await waitFor(() =>
      expect(api.calls("POST /users")[0]?.body).toEqual({
        name: "Diego Rocha",
        email: "diego@example.com",
        password: "Str0ng-password",
        role: "TECHNICIAN",
      }),
    );
    await waitFor(() => expect(screen.queryByRole("button", { name: "Criar usuário" })).toBeNull());
  });

  it("adds, renames and retires categories", async () => {
    const user = userEvent.setup();
    const { api } = renderApp("/admin?tab=categories", {
      user: admin,
      api: {
        "GET /categories": categories,
        "POST /categories": { status: 201, body: categories[0] },
        "PATCH /categories/10": categories[0],
      },
    });

    await user.type(await screen.findByPlaceholderText("Ex.: Telefonia"), "Telefonia");
    await user.click(screen.getByRole("button", { name: "Adicionar" }));
    await waitFor(() =>
      expect(api.calls("POST /categories")[0]?.body).toEqual({ name: "Telefonia" }),
    );

    const hardware = screen.getByText("Hardware").closest("li")!;
    await user.click(within(hardware).getByRole("button", { name: "Renomear" }));
    const input = within(hardware).getByLabelText("Novo nome");
    await user.clear(input);
    await user.type(input, "Equipamentos");
    await user.click(within(hardware).getByRole("button", { name: "Salvar" }));
    await waitFor(() =>
      expect(api.calls("PATCH /categories/10")[0]?.body).toEqual({ name: "Equipamentos" }),
    );
  });
});
