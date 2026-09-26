import { useSearchParams } from "react-router";
import { CategoriesPanel } from "../components/admin/CategoriesPanel";
import { UsersPanel } from "../components/admin/UsersPanel";
import { PageHeader } from "../components/ui";

const TABS = [
  { id: "users", label: "Usuários" },
  { id: "categories", label: "Categorias" },
] as const;

export function AdminPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") === "categories" ? "categories" : "users";

  return (
    <>
      <PageHeader eyebrow="Configuração" title="Administração" />
      <div role="tablist" aria-label="Seções" className="mb-4 flex gap-1">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            onClick={() => setSearchParams({ tab: item.id }, { replace: true })}
            className={`rounded-md px-3.5 py-1.5 text-sm transition-colors ${
              tab === item.id
                ? "bg-ink font-medium text-white"
                : "text-ink-soft hover:bg-ink/5 hover:text-ink"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div role="tabpanel">{tab === "users" ? <UsersPanel /> : <CategoriesPanel />}</div>
    </>
  );
}
