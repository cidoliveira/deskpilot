import { Link } from "react-router";

export interface BarItem {
  key: string;
  label: string;
  value: number;
  /** Optional drill-down: the bar opens the matching ticket list. */
  href?: string;
}

/**
 * Single-series horizontal bars: one hue, the value always written next to the bar
 * (never color alone), a recessive track, and a tooltip with the exact number.
 */
export function BarList({
  items,
  emptyText = "Sem dados no período.",
}: {
  items: BarItem[];
  emptyText?: string;
}) {
  const max = Math.max(...items.map((item) => item.value), 1);
  if (items.length === 0) return <p className="text-sm text-ink-soft">{emptyText}</p>;

  return (
    <ul className="space-y-2.5">
      {items.map((item) => {
        const row = (
          <>
            <span className="w-36 shrink-0 truncate text-sm text-ink-soft">{item.label}</span>
            <span className="h-2 flex-1 rounded bg-mist">
              <span
                className="block h-full rounded bg-accent"
                style={{ width: `${(item.value / max) * 100}%`, minWidth: item.value ? 4 : 0 }}
              />
            </span>
            <span className="w-8 text-right font-mono text-sm text-ink">{item.value}</span>
          </>
        );
        return (
          <li key={item.key} title={`${item.label}: ${item.value}`}>
            {item.href ? (
              <Link
                to={item.href}
                className="-mx-2 flex items-center gap-3 rounded px-2 py-0.5 hover:bg-mist/70"
              >
                {row}
              </Link>
            ) : (
              <div className="flex items-center gap-3">{row}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
