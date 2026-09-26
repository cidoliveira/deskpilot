import { formatDateTime } from "../../lib/format";
import { describeEvent } from "../../lib/events";
import type { TicketEvent } from "../../types/api";

export function HistoryTimeline({ events }: { events: TicketEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-ink-soft">Nenhuma mudança registrada ainda.</p>;
  }
  return (
    <ol className="relative space-y-4 border-l border-line pl-4">
      {events.map((event) => (
        <li key={event.id} className="relative">
          <span
            aria-hidden="true"
            className="absolute top-1.5 -left-[21px] size-2.5 rounded-full border-2 border-surface bg-ink-faint"
          />
          <p className="text-sm">
            <span className="font-medium">{event.changed_by.name}</span>{" "}
            <span className="text-ink-soft">{describeEvent(event)}</span>
          </p>
          <time dateTime={event.created_at} className="font-mono text-[11px] text-ink-faint">
            {formatDateTime(event.created_at)}
          </time>
        </li>
      ))}
    </ol>
  );
}
