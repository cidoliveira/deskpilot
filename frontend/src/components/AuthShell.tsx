import type { ReactNode } from "react";
import { usePageTitle } from "../hooks/usePageTitle";
import { Brand } from "./AppLayout";

/** Two-panel frame for login and sign-up: the deck on the left, the form on the right. */
export function AuthShell({ title, children }: { title: string; children: ReactNode }) {
  usePageTitle(title);
  return (
    <div className="min-h-screen md:grid md:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <div className="flex flex-col justify-between bg-deck px-8 py-8 text-[#dfe6ef] md:px-12 md:py-12">
        <Brand />
        <div className="hidden md:block">
          <p className="label-caps text-[#7f93b0]">Central de chamados de TI</p>
          <p className="mt-3 max-w-sm font-display text-3xl leading-tight font-semibold text-white">
            Cada chamado com dono, prazo e histórico.
          </p>
          {/* The SLA strip, as a quiet preview of the product's main instrument. */}
          <div className="mt-8 max-w-sm space-y-3" aria-hidden="true">
            {[
              ["#3fb6a8", "38%"],
              ["#d99a00", "84%"],
              ["#d1453b", "100%"],
            ].map(([color, width]) => (
              <div key={color} className="h-1.5 rounded-full bg-white/10">
                <div className="h-full rounded-full" style={{ width, background: color }} />
              </div>
            ))}
          </div>
        </div>
        <p className="hidden text-xs text-[#7f93b0] md:block">
          Projeto de portfólio · FastAPI + React
        </p>
      </div>
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <h1 className="mb-6 font-display text-2xl font-semibold">{title}</h1>
          {children}
        </div>
      </div>
    </div>
  );
}
