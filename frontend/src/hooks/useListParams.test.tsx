import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { useListParams } from "./useListParams";

function paramsFor(url: string) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>
  );
  return renderHook(() => useListParams(), { wrapper }).result.current.apiParams;
}

describe("useListParams", () => {
  it("turns URL filters into API parameters", () => {
    const params = paramsFor(
      "/tickets?status=OPEN,IN_PROGRESS&priority=HIGH&category_id=3&sla_status=AT_RISK&page=2",
    );

    expect(params).toMatchObject({
      status: ["OPEN", "IN_PROGRESS"],
      priority: ["HIGH"],
      category_id: 3,
      sla_status: "AT_RISK",
      page: 2,
    });
  });

  it("ignores values the API does not know (edited or old links)", () => {
    const params = paramsFor(
      "/tickets?status=OPEN,DONE&priority=URGENT&category_id=abc&sla_status=LATE",
    );

    expect(params.status).toEqual(["OPEN"]);
    expect(params.priority).toBeUndefined();
    expect(params.category_id).toBeUndefined();
    expect(params.sla_status).toBeUndefined();
  });
});
