import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ana, carla, categories, comments, history, makeDetail } from "../test/fixtures";
import { renderApp, reply } from "../test/renderApp";

/** Fake ticket endpoints. GET returns `state.ticket`, so a test can make a change stick
 *  on the "server", as the real API would when the app refetches after a mutation. */
function detailApi(detail = makeDetail()) {
  const state = { ticket: detail };
  return {
    state,
    [`GET /tickets/${detail.id}`]: () => state.ticket,
    [`GET /tickets/${detail.id}/history`]: history,
    [`GET /tickets/${detail.id}/comments`]: comments,
    "GET /categories": categories,
  };
}

describe("TicketDetailPage", () => {
  it("shows the ticket, its SLA, conversation and history", async () => {
    renderApp("/tickets/42", { user: ana, api: detailApi() });

    expect(await screen.findByRole("heading", { name: "VPN não conecta" })).toBeInTheDocument();
    expect(screen.getByText("Erro 809 ao conectar de casa.")).toBeInTheDocument();
    expect(await screen.findByText("Pode mandar um print?")).toBeInTheDocument();
    expect(await screen.findByText("abriu o chamado")).toBeInTheDocument();
    expect(screen.getByText("assumiu o chamado")).toBeInTheDocument(); // Carla assigned herself
    expect(screen.getAllByRole("meter").length).toBeGreaterThan(0);
    expect(document.title).toBe("#0042 VPN não conecta · DeskPilot");
  });

  it("explains when the ticket does not exist or is not visible", async () => {
    renderApp("/tickets/999", {
      user: ana,
      api: {
        "GET /tickets/999": reply(404, { error: "ticket_not_found", message: "Ticket not found" }),
        "GET /tickets/999/history": reply(404, { error: "ticket_not_found", message: "x" }),
      },
    });

    expect(await screen.findByText("Chamado não encontrado")).toBeInTheDocument();
  });

  it("sends a message and shows it in the conversation", async () => {
    const user = userEvent.setup();
    const { api } = renderApp("/tickets/42", {
      user: ana,
      api: {
        ...detailApi(),
        "POST /tickets/42/comments": {
          status: 201,
          body: { ...comments[0], id: 2, message: "Mandei agora." },
        },
      },
    });

    await user.type(await screen.findByLabelText("Nova mensagem"), "  Mandei agora.  ");
    await user.click(screen.getByRole("button", { name: "Enviar mensagem" }));

    await waitFor(() =>
      expect(api.calls("POST /tickets/42/comments")[0]?.body).toEqual({ message: "Mandei agora." }),
    );
    expect(screen.getByLabelText("Nova mensagem")).toHaveValue("");
  });

  it("tells the author when the technician is waiting for an answer", async () => {
    renderApp("/tickets/42", {
      user: ana,
      api: detailApi(makeDetail({ status: "WAITING_USER" })),
    });

    expect(await screen.findByText(/O técnico aguarda a sua resposta/)).toBeInTheDocument();
  });

  it("closes the conversation of a closed ticket", async () => {
    renderApp("/tickets/42", {
      user: ana,
      api: detailApi(
        makeDetail(
          {
            status: "CLOSED",
            resolution: "Perfil recriado.",
            resolved_at: new Date().toISOString(),
          },
          { can_comment: false },
        ),
      ),
    });

    expect(
      await screen.findByText("Chamado encerrado: não recebe novas mensagens."),
    ).toBeInTheDocument();
    expect(screen.getByText("Perfil recriado.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Nova mensagem")).not.toBeInTheDocument();
  });

  it("lets an allowed user edit the ticket in place", async () => {
    const user = userEvent.setup();
    const updated = makeDetail({ title: "VPN cai a cada 5 minutos" }, { can_edit: true });
    const fake = detailApi(makeDetail({}, { can_edit: true }));
    const { api } = renderApp("/tickets/42", {
      user: ana,
      api: { ...fake, "PATCH /tickets/42": () => (fake.state.ticket = updated) },
    });

    await user.click(await screen.findByRole("button", { name: "Editar" }));
    const title = screen.getByLabelText("Resumo");
    await user.clear(title);
    await user.type(title, "VPN cai a cada 5 minutos");
    await user.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(
      await screen.findByRole("heading", { name: "VPN cai a cada 5 minutos" }),
    ).toBeInTheDocument();
    expect(api.calls("PATCH /tickets/42")[0].body).toMatchObject({
      title: "VPN cai a cada 5 minutos",
      category_id: 11,
    });
  });

  it("lets the assigned technician claim, then shows the new state", async () => {
    const user = userEvent.setup();
    const claimed = makeDetail(
      { assigned_to: { id: carla.id, name: carla.name } },
      { allowed_transitions: ["IN_PROGRESS"] },
    );
    const fake = detailApi(makeDetail({}, { can_claim: true }));
    const { api } = renderApp("/tickets/42", {
      user: carla,
      api: { ...fake, "PUT /tickets/42/assignee": () => (fake.state.ticket = claimed) },
    });

    await user.click(await screen.findByRole("button", { name: "Assumir chamado" }));

    expect(await screen.findByRole("button", { name: "Iniciar atendimento" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Você assumiu o chamado.");
    expect(api.calls("PUT /tickets/42/assignee")[0].body).toEqual({ assignee_id: carla.id });
  });
});
