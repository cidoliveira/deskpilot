import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { TicketActions as Actions, TicketDetail, User } from "../../types/api";
import { TicketActions } from "./TicketActions";

const NO_ACTIONS: Actions = {
  can_edit: false,
  can_claim: false,
  can_assign: false,
  can_change_priority: false,
  can_comment: true,
  allowed_transitions: [],
};

const technician: User = {
  id: 7,
  name: "Carla",
  email: "carla@example.com",
  role: "TECHNICIAN",
  is_active: true,
  created_at: "2026-03-01T00:00:00Z",
  updated_at: "2026-03-01T00:00:00Z",
};

function ticket(status: TicketDetail["status"], actions: Partial<Actions>): TicketDetail {
  return {
    id: 42,
    title: "VPN não conecta",
    description: "Erro 809 desde ontem.",
    status,
    priority: "HIGH",
    category: { id: 1, name: "Network" },
    created_by: { id: 1, name: "Ana" },
    assigned_to: null,
    created_at: "2026-03-02T09:00:00Z",
    updated_at: "2026-03-02T09:00:00Z",
    resolved_at: null,
    closed_at: null,
    resolution: null,
    sla_due_at: "2026-03-02T17:00:00Z",
    sla_status: "ON_TRACK",
    allowed_actions: { ...NO_ACTIONS, ...actions },
  };
}

function renderActions(detail: TicketDetail) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <TicketActions ticket={detail} currentUser={technician} />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("TicketActions", () => {
  it("offers only what the API allows", () => {
    renderActions(ticket("OPEN", { can_claim: true }));

    expect(screen.getByRole("button", { name: "Assumir chamado" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resolver" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Prioridade")).not.toBeInTheDocument();
  });

  it("says so when nothing is allowed", () => {
    renderActions(ticket("CLOSED", {}));

    expect(screen.getByText("Nenhuma ação disponível para você agora.")).toBeInTheDocument();
  });

  it("names transitions after what they do in context", () => {
    renderActions(ticket("RESOLVED", { allowed_transitions: ["CLOSED", "IN_PROGRESS"] }));

    expect(screen.getByRole("button", { name: "Confirmar e fechar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reabrir chamado" })).toBeInTheDocument();
  });

  it("asks for the solution before resolving and sends it", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(ticket("RESOLVED", {})), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderActions(ticket("IN_PROGRESS", { allowed_transitions: ["WAITING_USER", "RESOLVED"] }));

    await user.click(screen.getByRole("button", { name: "Resolver" }));
    const confirm = screen.getByRole("button", { name: "Marcar como resolvido" });
    expect(confirm).toBeDisabled(); // no solution written yet
    expect(fetchMock).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText("O que resolveu o problema?"), "Perfil da VPN recriado.");
    await user.click(confirm);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/tickets/42/status");
    expect(JSON.parse(init.body)).toEqual({
      status: "RESOLVED",
      resolution: "Perfil da VPN recriado.",
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Status alterado para Resolvido.");
  });

  it("asks for confirmation before cancelling", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderActions(ticket("OPEN", { allowed_transitions: ["CANCELLED"] }));

    await user.click(screen.getByRole("button", { name: "Cancelar chamado" }));

    expect(screen.getByText(/não pode ser reaberto/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
