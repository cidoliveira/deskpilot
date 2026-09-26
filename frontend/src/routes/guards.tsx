import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "../auth/useAuth";
import { Spinner } from "../components/ui";
import type { UserRole } from "../types/api";

/** Screens for logged-in users only. Remembers the page to return to after signing in,
 *  except after "Sair": the next person to log in must not land on someone else's page. */
export function RequireAuth() {
  const { user, isLoading, signedOut } = useAuth();
  const location = useLocation();

  if (isLoading) return <Spinner label="Verificando sessão…" />;
  if (!user) {
    const from = location.pathname + location.search;
    return <Navigate to="/login" replace state={signedOut ? undefined : { from }} />;
  }
  return <Outlet />;
}

/**
 * Hides screens a role cannot use. This is navigation only: the API enforces every rule
 * on its own, so a user forcing the URL still gets 403/404 from the backend.
 */
export function RequireRole({ roles }: { roles: UserRole[] }) {
  const { user } = useAuth();
  if (!user || !roles.includes(user.role)) return <Navigate to="/" replace />;
  return <Outlet />;
}

/** Landing screen depends on the job: admins see the panel, technicians the queue. */
export function HomeRedirect() {
  const { user } = useAuth();
  if (user?.role === "ADMIN") return <Navigate to="/dashboard" replace />;
  if (user?.role === "TECHNICIAN") return <Navigate to="/queue" replace />;
  return <Navigate to="/tickets" replace />;
}
