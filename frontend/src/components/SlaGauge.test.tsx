import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SlaGauge } from "./SlaGauge";

const hoursAgo = (h: number) => new Date(Date.now() - h * 3_600_000).toISOString();
const inHours = (h: number) => new Date(Date.now() + h * 3_600_000).toISOString();

describe("SlaGauge", () => {
  it("shows how much of the window is used and the time left", () => {
    render(
      <SlaGauge status="AT_RISK" createdAt={hoursAgo(7)} dueAt={inHours(1)} resolvedAt={null} />,
    );

    const meter = screen.getByRole("meter", { name: "Prazo de SLA consumido" });
    expect(meter).toHaveAttribute("aria-valuenow", "88");
    expect(screen.getByText(/Vence em (59|60) min|Vence em 1 h/)).toBeInTheDocument();
  });

  it("tells how long ago an open ticket became overdue", () => {
    render(
      <SlaGauge status="BREACHED" createdAt={hoursAgo(6)} dueAt={hoursAgo(2)} resolvedAt={null} />,
    );

    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "100");
    expect(screen.getByText("Vencido há 2 h")).toBeInTheDocument();
  });

  it("says how late a ticket was resolved, not that it is still overdue", () => {
    render(
      <SlaGauge
        status="BREACHED"
        createdAt={hoursAgo(30)}
        dueAt={hoursAgo(22)}
        resolvedAt={hoursAgo(19)}
      />,
    );

    expect(screen.getByText("Resolvido com 3 h de atraso")).toBeInTheDocument();
    expect(screen.queryByText(/Vencido/)).not.toBeInTheDocument();
  });

  it("says when a ticket was resolved on time", () => {
    render(
      <SlaGauge
        status="MET"
        createdAt={hoursAgo(10)}
        dueAt={hoursAgo(2)}
        resolvedAt={hoursAgo(8)}
        size="panel"
      />,
    );

    expect(screen.getByText("Cumprido")).toBeInTheDocument();
    expect(screen.getByText("Resolvido no prazo")).toBeInTheDocument();
  });

  it("renders a neutral note for cancelled tickets", () => {
    render(<SlaGauge status={null} createdAt={hoursAgo(1)} dueAt={inHours(1)} resolvedAt={null} />);

    expect(screen.queryByRole("meter")).not.toBeInTheDocument();
    expect(screen.getByText("sem SLA")).toBeInTheDocument();
  });
});
