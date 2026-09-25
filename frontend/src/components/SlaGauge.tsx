import { formatDuration, slaProgress } from "../lib/format";
import { SLA_LABEL } from "../lib/labels";
import type { SlaStatus } from "../types/api";

const TONE: Record<SlaStatus, { bar: string; text: string }> = {
  ON_TRACK: { bar: "bg-sla-ok", text: "text-sla-ok" },
  AT_RISK: { bar: "bg-sla-risk", text: "text-[#9a6d00]" },
  BREACHED: { bar: "bg-sla-breach", text: "text-sla-breach" },
  MET: { bar: "bg-sla-met", text: "text-ink-soft" },
};

interface SlaGaugeProps {
  status: SlaStatus | null;
  createdAt: string;
  dueAt: string;
  resolvedAt: string | null;
  size?: "row" | "panel";
}

function caption(status: SlaStatus, remainingMs: number): string {
  if (status === "MET") return "Resolvido no prazo";
  if (status === "BREACHED") {
    return remainingMs < 0
      ? `Vencido há ${formatDuration(remainingMs)}`
      : "Resolvido fora do prazo";
  }
  return `Vence em ${formatDuration(remainingMs)}`;
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
  const text = caption(status, remainingMs);

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
