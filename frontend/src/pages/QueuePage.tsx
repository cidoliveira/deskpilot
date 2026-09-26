import { useAuth } from "../auth/useAuth";
import { TicketListView } from "../components/TicketListView";
import { PageHeader } from "../components/ui";
import { useListParams } from "../hooks/useListParams";
import { ACTIVE_STATUSES } from "../lib/labels";
import type { TicketListParams } from "../services/api";

interface QueueView {
  id: string;
  label: string;
  preset: Partial<TicketListParams>;
  empty: { title: string; hint: string };
  adminOnly?: boolean;
}

const VIEWS: QueueView[] = [
  {
    id: "mine",
    label: "Comigo",
    preset: { assignee: "me", status: ACTIVE_STATUSES },
    empty: { title: "Nada pendente com você", hint: "Assuma um chamado na aba Disponíveis." },
  },
  {
    id: "available",
    label: "Disponíveis",
    preset: { assignee: "none", status: ["OPEN"] },
    empty: { title: "Nenhum chamado esperando técnico", hint: "A fila está em dia." },
  },
  {
    id: "all",
    label: "Todos",
    preset: {},
    empty: { title: "Nenhum chamado ainda", hint: "Os chamados abertos aparecem aqui." },
    adminOnly: true,
  },
];

export function QueuePage() {
  const { user } = useAuth();
  // The queue is about urgency: the closest SLA deadline comes first.
  const list = useListParams("sla_due_at");
  const views = VIEWS.filter((view) => !view.adminOnly || user?.role === "ADMIN");
  const current = views.find((view) => view.id === list.searchParams.get("view")) ?? views[0];

  function selectView(id: string) {
    list.setSearchParams(new URLSearchParams({ view: id }), { replace: true });
  }

  return (
    <>
      <PageHeader eyebrow="Atendimento" title="Fila de atendimento" />
      <div role="tablist" aria-label="Visões da fila" className="mb-4 flex gap-1">
        {views.map((view) => (
          <button
            key={view.id}
            type="button"
            role="tab"
            aria-selected={view.id === current.id}
            onClick={() => selectView(view.id)}
            className={`rounded-md px-3.5 py-1.5 text-sm transition-colors ${
              view.id === current.id
                ? "bg-ink font-medium text-white"
                : "text-ink-soft hover:bg-ink/5 hover:text-ink"
            }`}
          >
            {view.label}
          </button>
        ))}
      </div>
      <TicketListView key={current.id} list={list} preset={current.preset} empty={current.empty} />
    </>
  );
}
