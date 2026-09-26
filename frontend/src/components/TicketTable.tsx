import { Link } from "react-router";
import { ticketCode, timeAgo } from "../lib/format";
import type { TicketSummary } from "../types/api";
import { PriorityBadge, StatusBadge } from "./Badges";
import { SlaGauge } from "./SlaGauge";

interface TicketTableProps {
  tickets: TicketSummary[];
  /** The author column matters to staff, not to someone looking at their own tickets. */
  showAuthor?: boolean;
}

export function TicketTable({ tickets, showAuthor = true }: TicketTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-line">
          <tr>
            <th scope="col" className="label-caps px-4 py-3 font-semibold">
              Chamado
            </th>
            <th scope="col" className="label-caps hidden px-3 py-3 font-semibold lg:table-cell">
              Prioridade
            </th>
            <th scope="col" className="label-caps px-3 py-3 font-semibold">
              Status
            </th>
            <th scope="col" className="label-caps hidden px-3 py-3 font-semibold md:table-cell">
              Responsável
            </th>
            <th scope="col" className="label-caps px-4 py-3 font-semibold">
              SLA
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {tickets.map((ticket) => (
            <tr key={ticket.id} className="group transition-colors hover:bg-mist/60">
              <td className="max-w-md px-4 py-3">
                <Link to={`/tickets/${ticket.id}`} className="block focus-visible:outline-offset-4">
                  <span className="font-mono text-xs text-ink-faint">{ticketCode(ticket.id)}</span>
                  <span className="mt-0.5 block truncate font-medium text-ink group-hover:text-accent-strong">
                    {ticket.title}
                  </span>
                  <span className="mt-0.5 block truncate text-xs text-ink-soft">
                    {ticket.category.name}
                    {showAuthor && ` · ${ticket.created_by.name}`} · {timeAgo(ticket.created_at)}
                  </span>
                </Link>
              </td>
              <td className="hidden px-3 py-3 lg:table-cell">
                <PriorityBadge priority={ticket.priority} />
              </td>
              <td className="px-3 py-3">
                <StatusBadge status={ticket.status} />
              </td>
              <td className="hidden px-3 py-3 text-ink-soft md:table-cell">
                {ticket.assigned_to?.name ?? <span className="text-ink-faint">Sem técnico</span>}
              </td>
              <td className="px-4 py-3">
                <SlaGauge
                  status={ticket.sla_status}
                  createdAt={ticket.created_at}
                  dueAt={ticket.sla_due_at}
                  resolvedAt={ticket.resolved_at}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
