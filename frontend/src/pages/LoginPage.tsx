import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation } from "react-router";
import { useAuth } from "../auth/useAuth";
import { AuthShell } from "../components/AuthShell";
import { TextField } from "../components/fields";
import { Button, ErrorBanner } from "../components/ui";

export function LoginPage() {
  const { user, login } = useAuth();
  const location = useLocation();
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  const from = (location.state as { from?: string } | null)?.from ?? "/";
  // Signed in (now or already): the one place that decides where to go, so the page the
  // visitor asked for before logging in is not lost to a race with another redirect.
  if (user) return <Navigate to={from} replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    setError(null);
    try {
      await login(String(form.get("email")), String(form.get("password")));
    } catch (err) {
      setError(err);
      setSubmitting(false);
    }
  }

  return (
    <AuthShell title="Entrar">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <ErrorBanner error={error} />
        <TextField label="E-mail" name="email" type="email" autoComplete="email" required />
        <TextField
          label="Senha"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
        <Button type="submit" busy={submitting} className="w-full">
          Entrar
        </Button>
      </form>
      <p className="mt-6 text-sm text-ink-soft">
        Ainda não tem conta?{" "}
        <Link to="/register" className="font-medium text-accent hover:underline">
          Criar conta
        </Link>
      </p>
    </AuthShell>
  );
}
