const dateTime = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatDateTime(iso: string): string {
  return dateTime.format(new Date(iso));
}

/** "#0042": ticket numbers read like the codes people say on the phone. */
export function ticketCode(id: number): string {
  return `#${String(id).padStart(4, "0")}`;
}

/** Compact duration: "45 min", "3 h 20 min", "2 d 4 h". */
export function formatDuration(ms: number): string {
  const minutes = Math.max(0, Math.round(Math.abs(ms) / 60_000));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    const rest = minutes % 60;
    return rest ? `${hours} h ${rest} min` : `${hours} h`;
  }
  const days = Math.floor(hours / 24);
  const restHours = hours % 24;
  return restHours ? `${days} d ${restHours} h` : `${days} d`;
}

export function timeAgo(iso: string, now: Date = new Date()): string {
  const ms = now.getTime() - new Date(iso).getTime();
  return ms < 60_000 ? "agora" : `há ${formatDuration(ms)}`;
}

export interface SlaProgress {
  /** Share of the SLA window used, 0..1 (capped; `overdue` tells if it went past). */
  fraction: number;
  overdue: boolean;
  /** Milliseconds until the due date (negative when overdue). */
  remainingMs: number;
}

/** How much of the SLA window has been used. Resolved tickets stop the clock. */
export function slaProgress(
  createdAt: string,
  dueAt: string,
  resolvedAt: string | null,
  now: Date = new Date(),
): SlaProgress {
  const start = new Date(createdAt).getTime();
  const due = new Date(dueAt).getTime();
  const end = resolvedAt ? new Date(resolvedAt).getTime() : now.getTime();
  const window = Math.max(due - start, 1);
  const used = (end - start) / window;
  return { fraction: Math.min(Math.max(used, 0), 1), overdue: end > due, remainingMs: due - end };
}
