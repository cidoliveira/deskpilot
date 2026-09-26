import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router";
import { useAuth } from "../auth/useAuth";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import { SlaGauge } from "../components/SlaGauge";
import { CommentThread } from "../components/ticket/CommentThread";
import { HistoryTimeline } from "../components/ticket/HistoryTimeline";
import { TicketActions } from "../components/ticket/TicketActions";
import { TicketEditForm } from "../components/ticket/TicketEditForm";
import { Button, Card, EmptyState, ErrorBanner, Spinner } from "../components/ui";
import { useTicket, useTicketHistory } from "../hooks/queries";
import { formatDateTime, ticketCode } from "../lib/format";
import { ApiError } from "../services/http";

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 text-sm">
      <dt className="text-ink-soft">{label}</dt>
      <dd className="text-right">{children}</dd>
    </div>
  );
}

export function TicketDetailPage() {
  const { user } = useAuth();
  const id = Number(useParams().id);
  const ticketQuery = useTicket(id);
  const history = useTicketHistory(id);
  const [editing, setEditing] = useState(false);

  if (ticketQuery.isPending) return <Spinner />;
  if (ticketQuery.error instanceof ApiError && ticketQuery.error.status === 404) {
    return (
      <EmptyState
        title="Chamado não encontrado"
        hint="Ele não existe ou não está disponível para o seu perfil."
        action={
          <Link to="/" className="text-sm font-medium text-accent hover:underline">
            Voltar para o início
          </Link>
        }
      />
    );
  }
  if (ticketQuery.isError || !user) return <ErrorBanner error={ticketQuery.error} />;

  const ticket = ticketQuery.data;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0 space-y-6">
        <header>
          <p className="font-mono text-sm text-ink-faint">{ticketCode(ticket.id)}</p>
          <div className="mt-1 flex flex-wrap items-start justify-between gap-3">
            <h1 className="font-display text-2xl font-semibold tracking-tight">{ticket.title}</h1>
            {ticket.allowed_actions.can_edit && !editing && (
              <Button variant="secondary" onClick={() => setEditing(true)}>
                Editar
              </Button>
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <StatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.priority} />
            <span className="text-sm text-ink-soft">{ticket.category.name}</span>
          </div>
          {/* Narrow screens: the deadline must be visible before scrolling to the side panel. */}
          <div className="mt-4 xl:hidden">
            <SlaGauge
              status={ticket.sla_status}
              createdAt={ticket.created_at}
              dueAt={ticket.sla_due_at}
              resolvedAt={ticket.resolved_at}
            />
          </div>
        </header>

        <Card className="p-5">
          {editing ? (
            <TicketEditForm ticket={ticket} onDone={() => setEditing(false)} />
          ) : (
            <>
              <h2 className="label-caps mb-2">Descrição</h2>
              <p className="text-sm leading-relaxed whitespace-pre-line">{ticket.description}</p>
            </>
          )}
        </Card>

        {ticket.resolution && (ticket.status === "RESOLVED" || ticket.status === "CLOSED") && (
          <Card className="border-sla-ok/30 p-5">
            <h2 className="label-caps mb-2">Solução</h2>
            <p className="text-sm leading-relaxed whitespace-pre-line">{ticket.resolution}</p>
            {ticket.status === "RESOLVED" && ticket.created_by.id === user.id && (
              <p className="mt-3 text-xs text-ink-soft">
                Funcionou? Confirme para fechar o chamado, ou reabra se o problema continuar.
              </p>
            )}
          </Card>
        )}

        <CommentThread ticket={ticket} currentUser={user} />
      </div>

      <aside className="space-y-4">
        <Card className="p-5">
          <h2 className="label-caps mb-3">Prazo de SLA</h2>
          <SlaGauge
            size="panel"
            status={ticket.sla_status}
            createdAt={ticket.created_at}
            dueAt={ticket.sla_due_at}
            resolvedAt={ticket.resolved_at}
          />
          <p className="mt-2 font-mono text-[11px] text-ink-faint">
            Vence {formatDateTime(ticket.sla_due_at)}
          </p>
        </Card>

        <Card className="p-5">
          <h2 className="label-caps mb-3">Ações</h2>
          <TicketActions ticket={ticket} currentUser={user} />
        </Card>

        <Card className="p-5">
          <h2 className="label-caps mb-2">Detalhes</h2>
          <dl className="divide-y divide-line">
            <Fact label="Aberto por">{ticket.created_by.name}</Fact>
            <Fact label="Técnico">
              {ticket.assigned_to?.name ?? <span className="text-ink-faint">Sem técnico</span>}
            </Fact>
            <Fact label="Aberto em">
              <span className="font-mono text-xs">{formatDateTime(ticket.created_at)}</span>
            </Fact>
            <Fact label="Atualizado em">
              <span className="font-mono text-xs">{formatDateTime(ticket.updated_at)}</span>
            </Fact>
            {ticket.resolved_at && (
              <Fact label="Resolvido em">
                <span className="font-mono text-xs">{formatDateTime(ticket.resolved_at)}</span>
              </Fact>
            )}
            {ticket.closed_at && (
              <Fact label="Encerrado em">
                <span className="font-mono text-xs">{formatDateTime(ticket.closed_at)}</span>
              </Fact>
            )}
          </dl>
        </Card>

        <Card className="p-5">
          <h2 className="label-caps mb-3">Histórico</h2>
          {history.isPending ? <Spinner /> : <HistoryTimeline events={history.data ?? []} />}
        </Card>
      </aside>
    </div>
  );
}
