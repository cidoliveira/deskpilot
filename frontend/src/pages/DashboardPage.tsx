import type { ReactNode } from "react";
import { Link } from "react-router";
import { BarList } from "../components/BarList";
import { Card, ErrorBanner, PageHeader, Spinner } from "../components/ui";
import { useDashboard } from "../hooks/queries";
import { formatDuration } from "../lib/format";
import { ACTIVE_STATUSES, PRIORITIES, PRIORITY_LABEL, STATUSES, STATUS_LABEL } from "../lib/labels";

interface HeadlineProps {
  label: string;
  value: string;
  caption: string;
  /** SLA signal: always paired with the label text, never the only cue. */
  signal?: "breach" | "risk" | "ok";
  href?: string;
}

const SIGNAL = { breach: "bg-sla-breach", risk: "bg-sla-risk", ok: "bg-sla-ok" };

function Headline({ label, value, caption, signal, href }: HeadlineProps) {
  const body = (
    <>
      <p className="label-caps flex items-center gap-2">
        {signal && <span aria-hidden="true" className={`size-2 rounded-sm ${SIGNAL[signal]}`} />}
        {label}
      </p>
      <p className="mt-2 font-display text-4xl font-semibold tracking-tight">{value}</p>
      <p className="mt-1 text-xs text-ink-soft">{caption}</p>
    </>
  );
  return (
    <Card className="p-5">
      {href ? (
        <Link to={href} className="block rounded focus-visible:outline-offset-8">
          {body}
        </Link>
      ) : (
        body
      )}
    </Card>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="p-5">
      <h2 className="label-caps mb-4">{title}</h2>
      {children}
    </Card>
  );
}

export function DashboardPage() {
  const { data, isPending, error } = useDashboard();
  if (isPending) return <Spinner />;
  if (error || !data) return <ErrorBanner error={error} />;

  const { sla } = data;
  const resolved = sla.met + sla.breached_resolved;
  const compliance =
    sla.compliance_rate === null ? "—" : `${Math.round(sla.compliance_rate * 100)}%`;
  const avg =
    data.avg_resolution_hours === null
      ? "—"
      : formatDuration(data.avg_resolution_hours * 3_600_000);
  const queue = (params: string) => `/queue?view=all&${params}`;

  return (
    <>
      <PageHeader eyebrow="Visão geral" title="Painel do service desk" />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Headline
          label="Fora do prazo agora"
          value={String(sla.breached_open)}
          caption="Chamados abertos com SLA vencido"
          signal="breach"
          href={queue(`sla_status=BREACHED&status=${ACTIVE_STATUSES.join(",")}`)}
        />
        <Headline
          label="Em risco"
          value={String(sla.at_risk)}
          caption="Com 80% ou mais do prazo consumido"
          signal="risk"
          href={queue("sla_status=AT_RISK")}
        />
        <Headline
          label="Cumprimento do SLA"
          value={compliance}
          caption={`${sla.met} de ${resolved} resolvidos dentro do prazo`}
          signal="ok"
        />
        <Headline
          label="Tempo médio de resolução"
          value={avg}
          caption={`${data.total} chamados no total`}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title="Chamados por status">
          <BarList
            items={STATUSES.map((status) => ({
              key: status,
              label: STATUS_LABEL[status],
              value: data.by_status[status],
              href: queue(`status=${status}`),
            }))}
          />
        </Panel>
        <Panel title="Chamados por prioridade">
          <BarList
            items={[...PRIORITIES].reverse().map((priority) => ({
              key: priority,
              label: PRIORITY_LABEL[priority],
              value: data.by_priority[priority],
              href: queue(`priority=${priority}`),
            }))}
          />
        </Panel>
        <Panel title="Chamados por categoria">
          <BarList
            items={data.by_category.map((item) => ({
              key: String(item.category_id),
              label: item.name,
              value: item.count,
              href: queue(`category_id=${item.category_id}`),
            }))}
          />
        </Panel>
        <Panel title="Carga por técnico">
          {data.by_technician.length === 0 ? (
            <p className="text-sm text-ink-soft">Nenhum chamado atribuído ainda.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left">
                  <th scope="col" className="label-caps pb-2 font-semibold">
                    Técnico
                  </th>
                  <th scope="col" className="label-caps pb-2 text-right font-semibold">
                    Em aberto
                  </th>
                  <th scope="col" className="label-caps pb-2 text-right font-semibold">
                    Resolvidos
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.by_technician.map((row) => (
                  <tr key={row.technician.id}>
                    <td className="py-2">{row.technician.name}</td>
                    <td className="py-2 text-right font-mono">{row.open}</td>
                    <td className="py-2 text-right font-mono">{row.resolved}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
      </div>
    </>
  );
}
