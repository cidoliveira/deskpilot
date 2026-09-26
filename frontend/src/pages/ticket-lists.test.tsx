import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { admin, ana, carla, categories, makeTicket, page } from "../test/fixtures";
import { renderApp } from "../test/renderApp";

describe("MyTicketsPage", () => {
  it("lists the user's own tickets with SLA and status", async () => {
    const { api } = renderApp("/tickets", {
      user: ana,
      api: {
        "GET /tickets": page([makeTicket({ sla_status: "AT_RISK" })]),
        "GET /categories": categories,
      },
    });

    const row = await screen.findByRole("row", { name: /VPN não conecta/ });
    expect(within(row).getByText("#0042")).toBeInTheDocument();
    expect(within(row).getAllByText("Aberto")[0]).toBeInTheDocument();
    expect(within(row).getAllByRole("meter")[0]).toHaveAccessibleName("Prazo de SLA consumido");
    expect(api.calls("GET /tickets")[0].query.get("created_by_id")).toBe(String(ana.id));
  });

  it("invites a first ticket instead of showing an empty table", async () => {
    renderApp("/tickets", {
      user: ana,
      api: { "GET /tickets": page([]), "GET /categories": categories },
    });

    expect(await screen.findByText("Você ainda não abriu nenhum chamado")).toBeInTheDocument();
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
  });

  it("sends the chosen filters to the API and keeps them in the URL", async () => {
    const user = userEvent.setup();
    const { api, router } = renderApp("/tickets", {
      user: ana,
      api: { "GET /tickets": page([makeTicket()]), "GET /categories": categories },
    });

    await user.selectOptions(await screen.findByLabelText("Prioridade"), "HIGH");
    await user.selectOptions(screen.getByLabelText("SLA"), "BREACHED");

    await waitFor(() => {
      const last = api.calls("GET /tickets").at(-1)!;
      expect(last.query.getAll("priority")).toEqual(["HIGH"]);
      expect(last.query.get("sla_status")).toBe("BREACHED");
    });
    expect(router.state.location.search).toContain("priority=HIGH");
  });

  it("pages through long lists", async () => {
    const user = userEvent.setup();
    const { api } = renderApp("/tickets", {
      user: ana,
      api: {
        "GET /tickets": page([makeTicket()], { total: 30, pages: 2 }),
        "GET /categories": categories,
      },
    });

    await user.click(await screen.findByRole("button", { name: "Próxima" }));

    await waitFor(() => expect(api.calls("GET /tickets").at(-1)!.query.get("page")).toBe("2"));
  });
});

describe("QueuePage", () => {
  it("starts with the technician's own active tickets, most urgent first", async () => {
    const { api } = renderApp("/queue", {
      user: carla,
      api: { "GET /tickets": page([makeTicket()]), "GET /categories": categories },
    });

    await screen.findByRole("row", { name: /VPN não conecta/ });
    const query = api.calls("GET /tickets")[0].query;
    expect(query.get("assignee")).toBe("me");
    expect(query.getAll("status")).toEqual(["OPEN", "IN_PROGRESS", "WAITING_USER"]);
    expect(query.get("sort")).toBe("sla_due_at");
  });

  it("switches to unassigned open tickets", async () => {
    const user = userEvent.setup();
    const { api } = renderApp("/queue", {
      user: carla,
      api: { "GET /tickets": page([]), "GET /categories": categories },
    });

    await user.click(await screen.findByRole("tab", { name: "Disponíveis" }));

    await waitFor(() => {
      const query = api.calls("GET /tickets").at(-1)!.query;
      expect(query.get("assignee")).toBe("none");
      expect(query.getAll("status")).toEqual(["OPEN"]);
    });
    expect(await screen.findByText("Nenhum chamado esperando técnico")).toBeInTheDocument();
  });

  it("gives admins a view of every ticket", async () => {
    renderApp("/queue", {
      user: admin,
      api: { "GET /tickets": page([]), "GET /categories": categories },
    });

    expect(await screen.findByRole("tab", { name: "Todos" })).toBeInTheDocument();
  });

  it("does not offer technicians the 'all tickets' view", async () => {
    renderApp("/queue", {
      user: carla,
      api: { "GET /tickets": page([]), "GET /categories": categories },
    });

    await screen.findByRole("tab", { name: "Comigo" });
    expect(screen.queryByRole("tab", { name: "Todos" })).not.toBeInTheDocument();
  });
});
