import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useAuth } from "../../auth/useAuth";
import { ROLE_LABEL } from "../../lib/labels";
import { usersApi } from "../../services/api";
import { ApiError } from "../../services/http";
import type { User, UserRole } from "../../types/api";
import { SelectField, TextField } from "../fields";
import { Pagination } from "../Pagination";
import { Button, Card, ErrorBanner, Spinner } from "../ui";

const ROLES = Object.keys(ROLE_LABEL) as UserRole[];

function NewUserForm({ onCreated }: { onCreated: () => void }) {
  const queryClient = useQueryClient();
  const create = useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["users"] });
      onCreated();
    },
  });
  const fieldError = (field: string) =>
    create.error instanceof ApiError ? create.error.fieldError(field) : undefined;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    create.mutate({
      name: String(form.get("name")),
      email: String(form.get("email")),
      password: String(form.get("password")),
      role: form.get("role") as UserRole,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4 border-b border-line p-5 md:grid-cols-2">
      {create.error instanceof ApiError && create.error.code !== "validation_error" && (
        <div className="md:col-span-2">
          <ErrorBanner error={create.error} />
        </div>
      )}
      <TextField label="Nome" name="name" error={fieldError("name")} />
      <TextField label="E-mail" name="email" type="email" error={fieldError("email")} />
      <TextField
        label="Senha inicial"
        name="password"
        type="password"
        autoComplete="new-password"
        hint="Pelo menos 8 caracteres. Combine a troca com a pessoa."
        error={fieldError("password")}
      />
      <SelectField label="Perfil" name="role" defaultValue="TECHNICIAN">
        {ROLES.map((role) => (
          <option key={role} value={role}>
            {ROLE_LABEL[role]}
          </option>
        ))}
      </SelectField>
      <div className="flex justify-end gap-2 md:col-span-2">
        <Button variant="ghost" onClick={onCreated}>
          Cancelar
        </Button>
        <Button type="submit" busy={create.isPending}>
          Criar usuário
        </Button>
      </div>
    </form>
  );
}

function UserRow({ user, isSelf }: { user: User; isSelf: boolean }) {
  const queryClient = useQueryClient();
  const update = useMutation({
    mutationFn: (data: Partial<Pick<User, "role" | "is_active">>) => usersApi.update(user.id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    // A list, not a table: on phones the controls wrap under the name instead of
    // pushing the page sideways.
    <li
      className={`flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3 ${
        user.is_active ? "" : "text-ink-faint"
      }`}
    >
      <div className="min-w-48 flex-1">
        <p className="font-medium">
          {user.name}
          {isSelf && <span className="ml-2 text-xs font-normal text-ink-soft">(você)</span>}
          {!user.is_active && <span className="ml-2 text-xs font-normal">desativado</span>}
        </p>
        <p className="truncate text-xs text-ink-soft">{user.email}</p>
        {update.error && (
          <div className="mt-2">
            <ErrorBanner error={update.error} />
          </div>
        )}
      </div>
      <div className="flex items-center gap-3">
        <label className="sr-only" htmlFor={`role-${user.id}`}>
          Perfil de {user.name}
        </label>
        <select
          id={`role-${user.id}`}
          value={user.role}
          disabled={isSelf || update.isPending}
          onChange={(event) => update.mutate({ role: event.target.value as UserRole })}
          className="rounded-md border border-line bg-surface px-2 py-1.5 text-sm disabled:opacity-60"
        >
          {ROLES.map((role) => (
            <option key={role} value={role}>
              {ROLE_LABEL[role]}
            </option>
          ))}
        </select>
        <Button
          variant={user.is_active ? "secondary" : "primary"}
          disabled={isSelf}
          busy={update.isPending}
          onClick={() => update.mutate({ is_active: !user.is_active })}
          className="min-w-28"
        >
          {user.is_active ? "Desativar" : "Reativar"}
        </Button>
      </div>
    </li>
  );
}

export function UsersPanel() {
  const { user: currentUser } = useAuth();
  const [page, setPage] = useState(1);
  const [role, setRole] = useState<UserRole | "">("");
  const [creating, setCreating] = useState(false);
  const params = { page, page_size: 20, role: role || undefined };
  const users = useQuery({
    queryKey: ["users", params],
    queryFn: () => usersApi.list(params),
    placeholderData: keepPreviousData,
  });

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3">
        <label className="flex items-center gap-2 text-sm">
          <span className="label-caps">Perfil</span>
          <select
            value={role}
            onChange={(event) => {
              setRole(event.target.value as UserRole | "");
              setPage(1);
            }}
            className="rounded-md border border-line bg-surface px-2 py-1 text-sm"
          >
            <option value="">Todos</option>
            {ROLES.map((value) => (
              <option key={value} value={value}>
                {ROLE_LABEL[value]}
              </option>
            ))}
          </select>
        </label>
        {!creating && <Button onClick={() => setCreating(true)}>Novo usuário</Button>}
      </div>
      {creating && <NewUserForm onCreated={() => setCreating(false)} />}
      {users.isPending && <Spinner />}
      <ErrorBanner error={users.error} />
      {users.data && (
        <>
          <ul aria-label="Usuários" className="divide-y divide-line text-sm">
            {users.data.items.map((user) => (
              <UserRow key={user.id} user={user} isSelf={user.id === currentUser?.id} />
            ))}
          </ul>
          <Pagination
            page={users.data.page}
            pages={users.data.pages}
            total={users.data.total}
            onChange={setPage}
            noun="usuários"
          />
        </>
      )}
    </Card>
  );
}
