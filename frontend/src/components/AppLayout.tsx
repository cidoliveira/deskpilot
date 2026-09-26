import { NavLink, Outlet } from "react-router";
import { useAuth } from "../auth/useAuth";
import { ROLE_LABEL } from "../lib/labels";
import type { UserRole } from "../types/api";

interface NavItem {
  to: string;
  label: string;
  roles: UserRole[];
}

const NAV: NavItem[] = [
  { to: "/dashboard", label: "Painel", roles: ["ADMIN"] },
  { to: "/queue", label: "Fila de atendimento", roles: ["TECHNICIAN", "ADMIN"] },
  { to: "/tickets", label: "Meus chamados", roles: ["USER", "TECHNICIAN", "ADMIN"] },
  { to: "/tickets/new", label: "Abrir chamado", roles: ["USER", "TECHNICIAN", "ADMIN"] },
  { to: "/admin", label: "Administração", roles: ["ADMIN"] },
];

export function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <img src="/favicon.svg" alt="" className="size-7" />
      <span className="font-display text-lg font-semibold tracking-tight">DeskPilot</span>
    </div>
  );
}

export function AppLayout() {
  const { user, logout } = useAuth();
  if (!user) return null;
  const items = NAV.filter((item) => item.roles.includes(user.role));

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[232px_1fr]">
      <aside className="bg-deck text-[#dfe6ef]">
        {/* The column fills the page height; only the inner menu sticks while scrolling. */}
        <div className="flex flex-col lg:sticky lg:top-0 lg:h-screen">
          <div className="flex items-center justify-between px-5 py-4 lg:py-6">
            <Brand />
            <button
              type="button"
              onClick={logout}
              className="text-sm text-[#9fb0c8] hover:text-white lg:hidden"
            >
              Sair
            </button>
          </div>
          <nav
            aria-label="Principal"
            className="flex [scrollbar-width:none] gap-1 overflow-x-auto px-3 pb-3 lg:flex-col"
          >
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end
                className={({ isActive }) =>
                  `rounded-md px-3 py-2 text-sm whitespace-nowrap transition-colors ${
                    isActive
                      ? "bg-deck-hover font-medium text-white shadow-[inset_3px_0_0_var(--color-accent)]"
                      : "text-[#b5c2d5] hover:bg-deck-hover hover:text-white"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto hidden border-t border-white/10 px-5 py-4 lg:block">
            <p className="truncate text-sm font-medium text-white">{user.name}</p>
            <p className="text-xs text-[#9fb0c8]">{ROLE_LABEL[user.role]}</p>
            <button
              type="button"
              onClick={logout}
              className="mt-3 text-sm text-[#9fb0c8] underline-offset-4 hover:text-white hover:underline"
            >
              Sair
            </button>
          </div>
        </div>
      </aside>
      <main className="mx-auto w-full max-w-6xl px-4 py-6 lg:px-8 lg:py-10">
        <Outlet />
      </main>
    </div>
  );
}
