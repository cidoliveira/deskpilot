import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "../auth/useAuth";
import { Spinner } from "../components/ui";
import type { UserRole } from "../types/api";

/** Screens for logged-in users only; remembers where the user wanted to go. */
export function RequireAuth() {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <Spinner label="Verificando sessão…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
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
