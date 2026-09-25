import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, request, setUnauthorizedHandler, tokenStorage } from "./http";

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  setUnauthorizedHandler(() => {});
});

describe("request", () => {
  it("sends the bearer token and repeats array query params", async () => {
    tokenStorage.set("abc");
    const fetchMock = mockFetch(200, { ok: true });

    await request("/tickets", { query: { status: ["OPEN", "IN_PROGRESS"], q: "", page: 2 } });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/tickets?status=OPEN&status=IN_PROGRESS&page=2");
    expect(init.headers.Authorization).toBe("Bearer abc");
  });

  it("turns the API error contract into an ApiError", async () => {
    mockFetch(409, {
      error: "invalid_status_transition",
      message: "Cannot move ticket from CLOSED to IN_PROGRESS",
    });

    const error = await request("/tickets/1/status").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, code: "invalid_status_transition" });
  });

  it("exposes field validation messages", async () => {
    mockFetch(422, {
      error: "validation_error",
      message: "Invalid request",
      details: [{ field: "title", message: "String should have at least 5 characters" }],
    });

    const error = (await request("/tickets").catch((e: unknown) => e)) as ApiError;

    expect(error.fieldError("title")).toContain("at least 5");
    expect(error.fieldError("description")).toBeUndefined();
  });

  it("ends the session when an authenticated request gets 401", async () => {
    tokenStorage.set("expired");
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    mockFetch(401, { error: "token_expired", message: "Token has expired" });

    await request("/auth/me").catch(() => undefined);

    expect(handler).toHaveBeenCalledOnce();
  });

  it("does not end a session on a failed login (no token yet)", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    mockFetch(401, { error: "invalid_credentials", message: "Incorrect e-mail or password" });

    await request("/auth/login", { method: "POST" }).catch(() => undefined);

    expect(handler).not.toHaveBeenCalled();
  });

  it("reports a network failure with a friendly message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const error = (await request("/tickets").catch((e: unknown) => e)) as ApiError;

    expect(error.code).toBe("network_error");
    expect(error.status).toBe(0);
  });
});
