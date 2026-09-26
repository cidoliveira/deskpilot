import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { RouteErrorPage } from "./RouteErrorPage";

function Broken(): never {
  throw new Error("render failed");
}

describe("RouteErrorPage", () => {
  it("replaces a crashed screen with a way out", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {}); // React logs the thrown error
    const router = createMemoryRouter([
      { path: "/", element: <Broken />, errorElement: <RouteErrorPage /> },
    ]);

    render(<RouterProvider router={router} />);

    expect(await screen.findByText("Esta tela parou de funcionar")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Recarregar" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para o início" })).toHaveAttribute("href", "/");
  });
});
