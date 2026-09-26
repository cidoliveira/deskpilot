import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useCategories } from "../../hooks/queries";
import { categoriesApi } from "../../services/api";
import type { Category } from "../../types/api";
import { Button, Card, ErrorBanner, Spinner } from "../ui";

function useInvalidateCategories() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["categories"] });
}

function CategoryRow({ category }: { category: Category }) {
  const invalidate = useInvalidateCategories();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(category.name);
  const update = useMutation({
    mutationFn: (data: Partial<Pick<Category, "name" | "is_active">>) =>
      categoriesApi.update(category.id, data),
    onSuccess: () => {
      setEditing(false);
      void invalidate();
    },
  });

  return (
    <li className="flex flex-wrap items-center gap-3 px-5 py-3">
      <div className="min-w-0 flex-1">
        {editing ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              update.mutate({ name: name.trim() });
            }}
            className="flex gap-2"
          >
            <label className="sr-only" htmlFor={`category-${category.id}`}>
              Novo nome
            </label>
            <input
              id={`category-${category.id}`}
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={50}
              autoFocus
              className="min-w-0 flex-1 rounded-md border border-line px-2.5 py-1.5 text-sm focus:border-accent focus:outline-none"
            />
            <Button type="submit" busy={update.isPending} disabled={name.trim().length < 2}>
              Salvar
            </Button>
            <Button variant="ghost" onClick={() => setEditing(false)}>
              Cancelar
            </Button>
          </form>
        ) : (
          <p className={category.is_active ? "font-medium" : "font-medium text-ink-faint"}>
            {category.name}
            {!category.is_active && <span className="ml-2 text-xs font-normal">inativa</span>}
          </p>
        )}
        {category.description && !editing && (
          <p className="truncate text-xs text-ink-soft">{category.description}</p>
        )}
        {update.error && (
          <div className="mt-2">
            <ErrorBanner error={update.error} />
          </div>
        )}
      </div>
      {!editing && (
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => setEditing(true)}>
            Renomear
          </Button>
          <Button
            variant="secondary"
            busy={update.isPending}
            onClick={() => update.mutate({ is_active: !category.is_active })}
          >
            {category.is_active ? "Desativar" : "Reativar"}
          </Button>
        </div>
      )}
    </li>
  );
}

export function CategoriesPanel() {
  const categories = useCategories(true);
  const invalidate = useInvalidateCategories();
  const [name, setName] = useState("");
  const create = useMutation({
    mutationFn: categoriesApi.create,
    onSuccess: () => {
      setName("");
      void invalidate();
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (name.trim().length >= 2) create.mutate({ name: name.trim() });
  }

  return (
    <Card>
      <form
        onSubmit={handleSubmit}
        className="flex flex-wrap items-end gap-2 border-b border-line p-5"
      >
        <label className="flex min-w-48 flex-1 flex-col gap-1">
          <span className="label-caps">Nova categoria</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={50}
            placeholder="Ex.: Telefonia"
            className="rounded-md border border-line px-2.5 py-1.5 text-sm focus:border-accent focus:outline-none"
          />
        </label>
        <Button type="submit" busy={create.isPending} disabled={name.trim().length < 2}>
          Adicionar
        </Button>
        {create.error && (
          <div className="w-full">
            <ErrorBanner error={create.error} />
          </div>
        )}
      </form>
      <p className="px-5 pt-3 text-xs text-ink-soft">
        Categorias não são apagadas: desativar tira a opção de novos chamados, e os antigos mantêm a
        categoria.
      </p>
      {categories.isPending && <Spinner />}
      <ul className="divide-y divide-line">
        {categories.data?.map((category) => (
          <CategoryRow key={category.id} category={category} />
        ))}
      </ul>
    </Card>
  );
}
