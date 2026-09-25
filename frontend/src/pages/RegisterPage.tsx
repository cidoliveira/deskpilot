import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router";
import { useAuth } from "../auth/useAuth";
import { AuthShell } from "../components/AuthShell";
import { TextField } from "../components/fields";
import { Button, ErrorBanner } from "../components/ui";
import { authApi } from "../services/api";
import { ApiError } from "../services/http";

export function RegisterPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;
  const fieldError = (field: string) =>
    error instanceof ApiError ? error.fieldError(field) : undefined;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const data = {
      name: String(form.get("name")),
      email: String(form.get("email")),
      password: String(form.get("password")),
    };
    setSubmitting(true);
    setError(null);
    try {
      await authApi.register(data);
      await login(data.email, data.password);
      navigate("/tickets/new", { replace: true });
    } catch (err) {
      setError(err);
      setSubmitting(false);
    }
  }

  const isValidation = error instanceof ApiError && error.code === "validation_error";

  return (
    <AuthShell title="Criar conta">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {!isValidation && <ErrorBanner error={error} />}
        <TextField label="Nome" name="name" autoComplete="name" error={fieldError("name")} />
        <TextField
          label="E-mail corporativo"
          name="email"
          type="email"
          autoComplete="email"
          error={fieldError("email")}
        />
        <TextField
          label="Senha"
          name="password"
          type="password"
          autoComplete="new-password"
          hint="Pelo menos 8 caracteres."
          error={fieldError("password")}
        />
        <Button type="submit" busy={submitting} className="w-full">
          Criar conta
        </Button>
      </form>
      <p className="mt-6 text-sm text-ink-soft">
        Já tem conta?{" "}
        <Link to="/login" className="font-medium text-accent hover:underline">
          Entrar
        </Link>
      </p>
    </AuthShell>
  );
}
