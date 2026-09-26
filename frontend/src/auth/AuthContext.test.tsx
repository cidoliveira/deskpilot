import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { tokenStorage } from "../services/http";
import { AuthProvider } from "./AuthContext";
import { useAuth } from "./useAuth";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const me = {
  id: 1,
  name: "Ana",
  email: "ana@example.com",
  role: "USER",
  is_active: true,
  created_at: "2026-03-01T00:00:00Z",
  updated_at: "2026-03-01T00:00:00Z",
};

function renderAuth() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
  return renderHook(() => useAuth(), { wrapper });
}

afterEach(() => vi.unstubAllGlobals());

describe("AuthProvider", () => {
  it("logs in and loads the current user", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          json(200, { access_token: "t1", token_type: "bearer", expires_in: 3600 }),
        )
        .mockResolvedValue(json(200, me)),
    );
    const { result } = renderAuth();

    await act(() => result.current.login("ana@example.com", "Str0ng-password"));

    await waitFor(() => expect(result.current.user?.name).toBe("Ana"));
    expect(tokenStorage.get()).toBe("t1");
  });

  it("does not keep a token when loading the user fails after login", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          json(200, { access_token: "t1", token_type: "bearer", expires_in: 3600 }),
        )
        .mockResolvedValue(json(500, { error: "internal_error", message: "boom" })),
    );
    const { result } = renderAuth();

    await expect(
      act(() => result.current.login("ana@example.com", "Str0ng-password")),
    ).rejects.toThrow();

    expect(tokenStorage.get()).toBeNull();
    expect(result.current.user).toBeNull();
  });

  it("logs out when the stored token is rejected", async () => {
    tokenStorage.set("expired");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(json(401, { error: "token_expired", message: "x" })),
    );
    const { result } = renderAuth();

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toBeNull();
    expect(tokenStorage.get()).toBeNull();
  });
});
