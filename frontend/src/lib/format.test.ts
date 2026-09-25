import { describe, expect, it } from "vitest";
import { formatDuration, slaProgress, ticketCode, timeAgo } from "./format";

const CREATED = "2026-03-02T09:00:00Z";
const DUE = "2026-03-02T17:00:00Z"; // 8 h window

describe("slaProgress", () => {
  it("measures the share of the window used so far", () => {
    const progress = slaProgress(CREATED, DUE, null, new Date("2026-03-02T15:00:00Z"));

    expect(progress.fraction).toBeCloseTo(0.75);
    expect(progress.overdue).toBe(false);
    expect(formatDuration(progress.remainingMs)).toBe("2 h");
  });

  it("caps the bar at full and flags overdue tickets", () => {
    const progress = slaProgress(CREATED, DUE, null, new Date("2026-03-02T18:30:00Z"));

    expect(progress.fraction).toBe(1);
    expect(progress.overdue).toBe(true);
    expect(formatDuration(progress.remainingMs)).toBe("1 h 30 min");
  });

  it("stops the clock when the ticket is resolved", () => {
    const progress = slaProgress(
      CREATED,
      DUE,
      "2026-03-02T11:00:00Z",
      new Date("2026-03-05T00:00:00Z"),
    );

    expect(progress.fraction).toBeCloseTo(0.25);
    expect(progress.overdue).toBe(false);
  });
});

describe("formatting", () => {
  it.each([
    [45 * 60_000, "45 min"],
    [3 * 3_600_000 + 20 * 60_000, "3 h 20 min"],
    [26 * 3_600_000, "1 d 2 h"],
    [48 * 3_600_000, "2 d"],
  ])("formats %i ms as %s", (ms, expected) => {
    expect(formatDuration(ms)).toBe(expected);
  });

  it("pads ticket codes", () => {
    expect(ticketCode(42)).toBe("#0042");
  });

  it("describes elapsed time", () => {
    const now = new Date("2026-03-02T12:00:00Z");
    expect(timeAgo("2026-03-02T11:59:30Z", now)).toBe("agora");
    expect(timeAgo("2026-03-02T09:00:00Z", now)).toBe("há 3 h");
  });
});
