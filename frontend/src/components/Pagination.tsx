import { Button } from "./ui";

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, pages, total, onChange }: PaginationProps) {
  if (pages <= 1) {
    return <p className="px-4 py-3 text-xs text-ink-soft">{total} chamado(s)</p>;
  }
  return (
    <nav
      aria-label="Paginação"
      className="flex items-center justify-between border-t border-line px-4 py-3"
    >
      <p className="text-xs text-ink-soft">
        {total} chamados · página <span className="font-mono">{page}</span> de{" "}
        <span className="font-mono">{pages}</span>
      </p>
      <div className="flex gap-2">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Anterior
        </Button>
        <Button variant="secondary" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          Próxima
        </Button>
      </div>
    </nav>
  );
}
