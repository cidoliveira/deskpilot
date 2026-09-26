import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ana, categories, comments, history, makeDetail } from "../test/fixtures";
import { renderApp } from "../test/renderApp";

describe("NewTicketPage", () => {
  it("checks the form before sending anything", async () => {
    const user = userEvent.setup();
    const { api } = renderApp("/tickets/new", {
      user: ana,
      api: { "GET /categories": categories },
    });

    await user.click(await screen.findByRole("button", { name: "Abrir chamado" }));

    expect(screen.getByText("Use pelo menos 5 caracteres.")).toBeInTheDocument();
    expect(screen.getByText("Escolha uma categoria.")).toBeInTheDocument();
    expect(api.calls("POST /tickets")).toHaveLength(0);
  });

  it("explains the SLA each priority means", async () => {
    const user = userEvent.setup();
    renderApp("/tickets/new", { user: ana, api: { "GET /categories": categories } });

    await user.selectOptions(await screen.findByLabelText("Prioridade"), "CRITICAL");

    expect(screen.getByText(/resolução em até 4 h/)).toBeInTheDocument();
  });

  it("opens the ticket and shows it", async () => {
    const user = userEvent.setup();
    const created = makeDetail({ id: 77, title: "Monitor não liga" });
    const { api, router } = renderApp("/tickets/new", {
      user: ana,
      api: {
        "GET /categories": categories,
        "POST /tickets": { status: 201, body: created },
        "GET /tickets/77": created,
        "GET /tickets/77/history": history,
        "GET /tickets/77/comments": comments,
      },
    });

    await user.type(await screen.findByLabelText("Resumo do problema"), "Monitor não liga");
    await user.selectOptions(screen.getByLabelText("Categoria"), "10");
    await user.type(screen.getByLabelText("Descrição"), "O monitor externo não liga desde hoje.");
    await user.click(screen.getByRole("button", { name: "Abrir chamado" }));

    expect(await screen.findByRole("heading", { name: "Monitor não liga" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/tickets/77");
    expect(api.calls("POST /tickets")[0].body).toEqual({
      title: "Monitor não liga",
      description: "O monitor externo não liga desde hoje.",
      category_id: 10,
      priority: "MEDIUM",
    });
  });
});
