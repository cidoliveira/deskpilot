import { describe, expect, it } from "vitest";
import type { TicketEvent } from "../types/api";
import { describeEvent } from "./events";

const event = (overrides: Partial<TicketEvent>): TicketEvent => ({
  id: 1,
  action: "CREATED",
  changed_by: { id: 7, name: "Carla" },
  old_value: null,
  new_value: null,
  old_label: null,
  new_label: null,
  created_at: "2026-03-02T09:00:00Z",
  ...overrides,
});

describe("describeEvent", () => {
  it("says a technician took the ticket when they assigned themselves", () => {
    expect(describeEvent(event({ action: "ASSIGNED", new_value: "7", new_label: "Carla" }))).toBe(
      "assumiu o chamado",
    );
  });

  it("describes a transfer between technicians", () => {
    const transfer = event({
      action: "ASSIGNED",
      old_value: "7",
      old_label: "Carla",
      new_value: "8",
      new_label: "Diego",
      changed_by: { id: 1, name: "Admin" },
    });
    expect(describeEvent(transfer)).toBe("transferiu de Carla para Diego");
  });

  it("translates statuses and priorities", () => {
    expect(
      describeEvent(
        event({ action: "STATUS_CHANGED", old_value: "OPEN", new_value: "IN_PROGRESS" }),
      ),
    ).toBe("mudou de Aberto para Em andamento");
    expect(
      describeEvent(event({ action: "PRIORITY_CHANGED", old_value: "LOW", new_value: "CRITICAL" })),
    ).toBe("mudou a prioridade de Baixa para Crítica");
  });

  it("uses category names, not ids", () => {
    const change = event({
      action: "CATEGORY_CHANGED",
      old_value: "3",
      old_label: "Network",
      new_value: "5",
      new_label: "Email",
    });
    expect(describeEvent(change)).toBe("mudou a categoria de Network para Email");
  });
});
