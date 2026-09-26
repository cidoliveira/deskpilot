import type { ReactNode } from "react";
import { Link } from "react-router";
import { BarList } from "../components/BarList";
import { SlaBacklogBar } from "../components/SlaBacklogBar";
import { Card, ErrorBanner, PageHeader, Spinner } from "../components/ui";
import { useDashboard } from "../hooks/queries";
import { formatDuration } from "../lib/format";
import { ACTIVE_STATUSES, PRIORITIES, PRIORITY_LABEL, STATUSES, STATUS_LABEL } from "../lib/labels";

function Fact({ label, value, caption }: { label: string; value: string; caption: string }) {
  return (
    <div>
      <p className="label-caps">{label}</p>
      <p className="mt-1 font-display text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-0.5 text-xs text-ink-soft">{caption}</p>
    </div>
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
  const activeStatuses = ACTIVE_STATUSES.join(",");
  const backlog = ACTIVE_STATUSES.reduce((sum, status) => sum + data.by_status[status], 0);

  return (
    <>
      <PageHeader eyebrow="Visão geral" title="Painel do service desk" />

      {sla.breached_open > 0 && (
        <Link
          to={queue(`sla_status=BREACHED&status=${activeStatuses}`)}
          className="mb-4 flex items-center justify-between gap-4 rounded-lg border border-l-4 border-sla-breach/30 border-l-sla-breach bg-surface px-5 py-3 text-sm hover:bg-sla-breach/5"
        >
          <span>
            <strong className="font-semibold">
              {sla.breached_open === 1
                ? "1 chamado em aberto já passou do prazo."
                : `${sla.breached_open} chamados em aberto já passaram do prazo.`}
            </strong>{" "}
            <span className="text-ink-soft">Priorize-os na fila.</span>
          </span>
          <span className="font-medium whitespace-nowrap text-sla-breach">Ver chamados →</span>
        </Link>
      )}

      <Card className="grid gap-6 p-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] lg:gap-10">
        <div>
          <h2 className="label-caps">Situação do SLA · chamados em aberto</h2>
          <p className="mt-1 mb-4 font-display text-3xl font-semibold tracking-tight">
            {backlog}{" "}
            <span className="font-sans text-sm font-normal text-ink-soft">
              {backlog === 1 ? "chamado aguardando solução" : "chamados aguardando solução"}
            </span>
          </p>
          <SlaBacklogBar
            segments={[
              {
                key: "ON_TRACK",
                label: "No prazo",
                count: Math.max(backlog - sla.at_risk - sla.breached_open, 0),
                href: queue(`sla_status=ON_TRACK&status=${activeStatuses}`),
              },
              {
                key: "AT_RISK",
                label: "Em risco",
                count: sla.at_risk,
                href: queue(`sla_status=AT_RISK&status=${activeStatuses}`),
              },
              {
                key: "BREACHED",
                label: "Fora do prazo",
                count: sla.breached_open,
                href: queue(`sla_status=BREACHED&status=${activeStatuses}`),
              },
            ]}
          />
        </div>
        <div className="grid grid-cols-2 gap-6 border-t border-line pt-5 lg:grid-cols-1 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-10">
          <Fact
            label="Cumprimento do SLA"
            value={compliance}
            caption={`${sla.met} de ${resolved} resolvidos dentro do prazo`}
          />
          <Fact
            label="Tempo médio de resolução"
            value={avg}
            caption={`sobre ${resolved} chamados resolvidos`}
          />
        </div>
      </Card>

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
