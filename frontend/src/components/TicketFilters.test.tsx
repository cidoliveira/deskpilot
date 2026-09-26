import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useListParams } from "../hooks/useListParams";
import { TicketFilters } from "./TicketFilters";

function Harness() {
  const list = useListParams();
  const location = useLocation();
  return (
    <>
      <TicketFilters
        filters={list.filters}
        setFilter={list.setFilter}
        clearFilters={list.clearFilters}
        hasFilters={list.hasFilters}
      />
      <output data-testid="url">{location.search}</output>
    </>
  );
}

function renderFilters(url: string) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("[]", { status: 200 })));
  const client = new QueryClient();
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>
        <Harness />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("TicketFilters", () => {
  it("clears the search box together with the URL filters", async () => {
    const user = userEvent.setup();
    renderFilters("/tickets?q=vpn&priority=HIGH");
    const search = screen.getByRole("searchbox", { name: "Buscar" });
    expect(search).toHaveValue("vpn");

    await user.click(screen.getByRole("button", { name: "Limpar filtros" }));

    expect(search).toHaveValue("");
    expect(screen.getByTestId("url")).toHaveTextContent(/^$/);
  });

  it("writes the search to the URL after a pause, keeping what is typed", async () => {
    const user = userEvent.setup();
    renderFilters("/tickets");
    const search = screen.getByRole("searchbox", { name: "Buscar" });

    await user.type(search, "impressora ");

    await vi.waitFor(() => expect(screen.getByTestId("url")).toHaveTextContent("?q=impressora"), {
      timeout: 2000,
    });
    expect(search).toHaveValue("impressora "); // trailing space not eaten
  });
});
