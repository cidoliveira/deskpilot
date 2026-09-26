import { formatDuration, slaProgress } from "../lib/format";
import { SLA_LABEL } from "../lib/labels";
import type { SlaStatus } from "../types/api";

const TONE: Record<SlaStatus, { bar: string; text: string }> = {
  ON_TRACK: { bar: "bg-sla-ok", text: "text-sla-ok-text" },
  AT_RISK: { bar: "bg-sla-risk", text: "text-sla-risk-text" },
  BREACHED: { bar: "bg-sla-breach", text: "text-sla-breach-text" },
  MET: { bar: "bg-sla-met", text: "text-ink-soft" },
};

interface SlaGaugeProps {
  status: SlaStatus | null;
  createdAt: string;
  dueAt: string;
  resolvedAt: string | null;
  size?: "row" | "panel";
}

/** Full sentence for the detail panel; `compact` for table rows, where space is short. */
function caption(
  status: SlaStatus,
  remainingMs: number,
  resolved: boolean,
  compact: boolean,
): string {
  const time = formatDuration(remainingMs);
  if (status === "MET") return compact ? "Cumprido" : "Resolvido no prazo";
  if (status === "BREACHED") {
    // remainingMs is measured at resolution time for resolved tickets (the clock stopped).
    if (resolved) return compact ? `${time} de atraso` : `Resolvido com ${time} de atraso`;
    return `Vencido há ${time}`;
  }
  return `Vence em ${time}`;
}

/**
 * How much of the SLA window has been used, as a thin instrument strip.
 * The one element in the UI that carries signal color: it answers "how urgent is this?"
 */
export function SlaGauge({ status, createdAt, dueAt, resolvedAt, size = "row" }: SlaGaugeProps) {
  if (status === null) {
    return <span className="font-mono text-xs text-ink-faint">sem SLA</span>;
  }

  const { fraction, remainingMs } = slaProgress(createdAt, dueAt, resolvedAt);
  const tone = TONE[status];
  const percent = Math.round(fraction * 100);
  const text = caption(status, remainingMs, resolvedAt !== null, size === "row");

  if (size === "panel") {
    return (
      <div>
        <div className="flex items-baseline justify-between">
          <span className={`font-display text-lg font-semibold ${tone.text}`}>
            {SLA_LABEL[status]}
          </span>
          <span className="font-mono text-xs text-ink-soft">{percent}% do prazo</span>
        </div>
        <div
          className="mt-2 h-2.5 overflow-hidden rounded-full bg-line"
          role="meter"
          aria-label="Prazo de SLA consumido"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-valuetext={`${SLA_LABEL[status]}: ${text}`}
        >
          <div
            className={`h-full rounded-full ${tone.bar} transition-[width] duration-700 ease-out`}
            style={{ width: `${percent}%` }}
          />
        </div>
        <p className="mt-1.5 font-mono text-xs text-ink-soft">{text}</p>
      </div>
    );
  }

  return (
    <div className="w-36" title={`${SLA_LABEL[status]} — ${text}`}>
      <div
        className="h-1.5 overflow-hidden rounded-full bg-line"
        role="meter"
        aria-label="Prazo de SLA consumido"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={`${SLA_LABEL[status]}: ${text}`}
      >
        <div className={`h-full rounded-full ${tone.bar}`} style={{ width: `${percent}%` }} />
      </div>
      <p className={`mt-1 truncate font-mono text-[11px] ${tone.text}`}>{text}</p>
    </div>
  );
}
