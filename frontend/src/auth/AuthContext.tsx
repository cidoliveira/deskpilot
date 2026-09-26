import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { authApi } from "../services/api";
import { setUnauthorizedHandler, tokenStorage } from "../services/http";
import { AuthContext, ME_QUERY_KEY, type AuthContextValue } from "./useAuth";

/**
 * Session state. The token is the only thing stored; the current user (and role) always
 * comes from GET /auth/me, the same way the backend reloads the user on every request.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState(() => tokenStorage.get());
  const [signedOut, setSignedOut] = useState(false);

  const me = useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: authApi.me,
    enabled: token !== null,
    retry: false,
    staleTime: 5 * 60_000,
  });

  const endSession = useCallback(
    (manual: boolean) => {
      tokenStorage.clear();
      setToken(null);
      setSignedOut(manual);
      queryClient.clear(); // no data from the previous session survives
    },
    [queryClient],
  );
  const logout = useCallback(() => endSession(true), [endSession]);

  // Any authenticated request answered with 401 (expired token, deactivated user) ends the
  // session too, but keeps the page, so the same person can sign in and continue.
  useEffect(() => setUnauthorizedHandler(() => endSession(false)), [endSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await authApi.login(email, password);
      tokenStorage.set(access_token);
      try {
        await queryClient.fetchQuery({ queryKey: ME_QUERY_KEY, queryFn: authApi.me });
        setSignedOut(false);
      } catch (error) {
        // Login failed halfway (e.g. network error): don't leave a session behind that a
        // page refresh would silently resume.
        tokenStorage.clear();
        throw error;
      }
      setToken(access_token);
    },
    [queryClient],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user: token ? (me.data ?? null) : null,
      isLoading: token !== null && me.isPending,
      login,
      logout,
      signedOut,
    }),
    [token, me.data, me.isPending, login, logout, signedOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
