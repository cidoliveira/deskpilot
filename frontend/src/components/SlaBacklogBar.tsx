import { Link } from "react-router";

export interface BacklogSegment {
  key: "ON_TRACK" | "AT_RISK" | "BREACHED";
  label: string;
  count: number;
  href: string;
}

const COLOR: Record<BacklogSegment["key"], string> = {
  ON_TRACK: "bg-sla-ok",
  AT_RISK: "bg-sla-risk",
  BREACHED: "bg-sla-breach",
};

/**
 * The open backlog split by SLA state: one bar, segments separated by a 2px gap, and a
 * labelled legend with counts (color is never the only cue). Each part opens the list.
 */
export function SlaBacklogBar({ segments }: { segments: BacklogSegment[] }) {
  const total = segments.reduce((sum, segment) => sum + segment.count, 0);
  if (total === 0) {
    return <p className="text-sm text-ink-soft">Nenhum chamado em aberto. Fila zerada.</p>;
  }

  return (
    <div>
      <div
        className="flex h-3 gap-0.5 overflow-hidden rounded"
        role="img"
        aria-label={segments.map((s) => `${s.label}: ${s.count}`).join(", ")}
      >
        {segments
          .filter((segment) => segment.count > 0)
          .map((segment) => (
            <div
              key={segment.key}
              className={`${COLOR[segment.key]} first:rounded-l last:rounded-r`}
              style={{ flexGrow: segment.count }}
              title={`${segment.label}: ${segment.count}`}
            />
          ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
        {segments.map((segment) => (
          <li key={segment.key}>
            <Link
              to={segment.href}
              className="group flex items-center gap-2 text-sm text-ink-soft hover:text-ink"
            >
              <span aria-hidden="true" className={`size-2.5 rounded-sm ${COLOR[segment.key]}`} />
              {segment.label}
              <span className="font-mono text-ink group-hover:underline">{segment.count}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
