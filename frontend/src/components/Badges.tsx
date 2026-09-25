import { PRIORITY_LABEL, STATUS_LABEL } from "../lib/labels";
import type { TicketPriority, TicketStatus } from "../types/api";

// Status badges stay neutral on purpose: color is reserved for SLA urgency.
const STATUS_STYLE: Record<TicketStatus, string> = {
  OPEN: "border-ink/25 text-ink",
  IN_PROGRESS: "border-accent/40 bg-accent-soft text-accent-strong",
  WAITING_USER: "border-dashed border-ink/35 text-ink-soft",
  RESOLVED: "border-ink/15 bg-mist text-ink-soft",
  CLOSED: "border-transparent bg-mist text-ink-faint",
  CANCELLED: "border-transparent bg-mist text-ink-faint line-through",
};

export function StatusBadge({ status }: { status: TicketStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium whitespace-nowrap ${STATUS_STYLE[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}

// Priority as a 4-step signal level (like bars of reception), readable without color.
const LEVEL: Record<TicketPriority, number> = { LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4 };

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  const level = LEVEL[priority];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs whitespace-nowrap text-ink">
      <span className="flex items-end gap-px" aria-hidden="true">
        {[1, 2, 3, 4].map((step) => (
          <span
            key={step}
            className={`w-[3px] rounded-sm ${step <= level ? "bg-ink" : "bg-line"}`}
            style={{ height: `${4 + step * 2}px` }}
          />
        ))}
      </span>
      <span className={priority === "CRITICAL" ? "font-semibold" : ""}>
        {PRIORITY_LABEL[priority]}
      </span>
    </span>
  );
}
