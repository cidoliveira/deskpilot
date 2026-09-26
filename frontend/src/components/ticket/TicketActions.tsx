import { useState } from "react";
import { useAssign, useChangePriority, useChangeStatus } from "../../hooks/mutations";
import { useStaff } from "../../hooks/queries";
import { PRIORITIES, PRIORITY_LABEL, STATUS_LABEL, TRANSITION_LABEL } from "../../lib/labels";
import type { TicketDetail, TicketPriority, TicketStatus, User } from "../../types/api";
import { Button, ErrorBanner } from "../ui";

function transitionLabel(from: TicketStatus, to: TicketStatus): string {
  if (to === "IN_PROGRESS" && from === "RESOLVED") return "Reabrir chamado";
  if (to === "IN_PROGRESS" && from === "WAITING_USER") return "Retomar atendimento";
  return TRANSITION_LABEL[to];
}

interface TicketActionsProps {
  ticket: TicketDetail;
  currentUser: User;
}

/** Renders only what `allowed_actions` (computed by the API) says the user can do. */
export function TicketActions({ ticket, currentUser }: TicketActionsProps) {
  const actions = ticket.allowed_actions;
  const changeStatus = useChangeStatus(ticket.id);
  const assign = useAssign(ticket.id);
  const changePriority = useChangePriority(ticket.id);
  const staff = useStaff(actions.can_assign);
  const [pending, setPending] = useState<TicketStatus | null>(null); // needs confirmation
  const [resolution, setResolution] = useState("");
  const [assignee, setAssignee] = useState("");
  // Confirmation of the last action, announced politely to screen readers too.
  const [notice, setNotice] = useState("");

  const error = changeStatus.error ?? assign.error ?? changePriority.error;
  const nothingToDo =
    !actions.can_claim &&
    !actions.can_assign &&
    !actions.can_change_priority &&
    actions.allowed_transitions.length === 0;

  const announcement = (
    <p role="status" aria-live="polite" className="text-sm text-sla-ok-text empty:hidden">
      {notice}
    </p>
  );

  if (nothingToDo) {
    return (
      <div className="space-y-2">
        {announcement}
        <p className="text-sm text-ink-soft">Nenhuma ação disponível para você agora.</p>
      </div>
    );
  }

  const statusChanged = (status: TicketStatus) => () =>
    setNotice(`Status alterado para ${STATUS_LABEL[status]}.`);

  function move(status: TicketStatus) {
    if (status === "RESOLVED" || status === "CANCELLED") {
      setPending(status); // ask for the resolution / a confirmation first
      return;
    }
    changeStatus.mutate({ status }, { onSuccess: statusChanged(status) });
  }

  function confirmPending() {
    if (!pending) return;
    const text = resolution.trim();
    if (pending === "RESOLVED" && text.length < 10) return;
    changeStatus.mutate(
      { status: pending, resolution: pending === "RESOLVED" ? text : undefined },
      {
        onSuccess: () => {
          setPending(null);
          statusChanged(pending)();
        },
      },
    );
  }

  return (
    <div className="space-y-4">
      {announcement}
      <ErrorBanner error={error} />

      {actions.can_claim && (
        <Button
          className="w-full"
          busy={assign.isPending}
          onClick={() =>
            assign.mutate(currentUser.id, {
              onSuccess: () => setNotice("Você assumiu o chamado."),
            })
          }
        >
          Assumir chamado
        </Button>
      )}

      {actions.allowed_transitions.length > 0 && !pending && (
        <div className="flex flex-col gap-2">
          {actions.allowed_transitions.map((status) => (
            <Button
              key={status}
              variant={
                status === "RESOLVED" || status === "CLOSED"
                  ? "primary"
                  : status === "CANCELLED"
                    ? "danger"
                    : "secondary"
              }
              busy={changeStatus.isPending && changeStatus.variables?.status === status}
              onClick={() => move(status)}
            >
              {transitionLabel(ticket.status, status)}
            </Button>
          ))}
        </div>
      )}

      {pending === "RESOLVED" && (
        <div className="space-y-2 rounded-md border border-line p-3">
          <label htmlFor="resolution" className="block text-sm font-medium">
            O que resolveu o problema?
          </label>
          <textarea
            id="resolution"
            value={resolution}
            onChange={(event) => setResolution(event.target.value)}
            rows={4}
            placeholder="Ex.: perfil da VPN recriado e certificado renovado."
            className="w-full rounded-md border border-line px-3 py-2 text-sm focus:border-accent focus:outline-none"
          />
          <p className="text-xs text-ink-soft">
            O usuário verá esta descrição e poderá confirmar ou reabrir.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setPending(null)}>
              Voltar
            </Button>
            <Button
              busy={changeStatus.isPending}
              disabled={resolution.trim().length < 10}
              onClick={confirmPending}
            >
              Marcar como resolvido
            </Button>
          </div>
        </div>
      )}

      {pending === "CANCELLED" && (
        <div className="space-y-2 rounded-md border border-sla-breach/30 p-3">
          <p className="text-sm">Cancelar este chamado? Ele sai da fila e não pode ser reaberto.</p>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setPending(null)}>
              Manter chamado
            </Button>
            <Button variant="danger" busy={changeStatus.isPending} onClick={confirmPending}>
              Cancelar chamado
            </Button>
          </div>
        </div>
      )}

      {actions.can_assign && (
        <div className="flex items-end gap-2">
          <label className="flex flex-1 flex-col gap-1">
            <span className="label-caps">Técnico responsável</span>
            <select
              value={assignee}
              onChange={(event) => setAssignee(event.target.value)}
              className="rounded-md border border-line bg-surface px-2.5 py-1.5 text-sm focus:border-accent focus:outline-none"
            >
              <option value="">{ticket.assigned_to ? "Transferir para…" : "Escolher…"}</option>
              {staff.data?.items
                .filter((tech) => tech.id !== ticket.assigned_to?.id)
                .map((tech) => (
                  <option key={tech.id} value={tech.id}>
                    {tech.name}
                  </option>
                ))}
              {ticket.assigned_to?.id !== currentUser.id && (
                <option value={currentUser.id}>Eu ({currentUser.name})</option>
              )}
            </select>
          </label>
          <Button
            variant="secondary"
            disabled={!assignee}
            busy={assign.isPending}
            onClick={() =>
              assign.mutate(Number(assignee), {
                onSuccess: (updated) => {
                  setAssignee("");
                  setNotice(`Chamado atribuído a ${updated.assigned_to?.name ?? "técnico"}.`);
                },
              })
            }
          >
            Atribuir
          </Button>
        </div>
      )}

      {actions.can_change_priority && (
        <label className="flex flex-col gap-1">
          <span className="label-caps">Prioridade</span>
          <select
            value={ticket.priority}
            disabled={changePriority.isPending}
            onChange={(event) =>
              changePriority.mutate(event.target.value as TicketPriority, {
                onSuccess: () => setNotice("Prioridade alterada; o prazo de SLA foi recalculado."),
              })
            }
            className="rounded-md border border-line bg-surface px-2.5 py-1.5 text-sm focus:border-accent focus:outline-none"
          >
            {PRIORITIES.map((value) => (
              <option key={value} value={value}>
                {PRIORITY_LABEL[value]}
              </option>
            ))}
          </select>
          <span className="text-xs text-ink-soft">
            Mudar a prioridade recalcula o prazo de SLA.
          </span>
        </label>
      )}
    </div>
  );
}
