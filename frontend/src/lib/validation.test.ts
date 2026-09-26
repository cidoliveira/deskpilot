import { describe, expect, it } from "vitest";
import { fieldMessage } from "./validation";

describe("fieldMessage", () => {
  it.each([
    [
      { field: "password", message: "x", type: "string_too_short", ctx: { min_length: 8 } },
      "Use pelo menos 8 caracteres.",
    ],
    [
      { field: "title", message: "x", type: "string_too_long", ctx: { max_length: 200 } },
      "Use no máximo 200 caracteres.",
    ],
    [
      { field: "message", message: "x", type: "string_too_short", ctx: { min_length: 1 } },
      "Preencha este campo.",
    ],
    [
      { field: "email", message: "x", type: "value_error", ctx: { reason: "no @" } },
      "Informe um e-mail válido, como nome@empresa.com.",
    ],
    [{ field: "name", message: "x", type: "missing" }, "Preencha este campo."],
    [{ field: "priority", message: "x", type: "enum" }, "Escolha um valor válido."],
  ])("translates %o", (detail, expected) => {
    expect(fieldMessage(detail)).toBe(expected);
  });

  it("falls back to the API message for unknown types", () => {
    expect(fieldMessage({ field: "x", message: "Something new", type: "brand_new" })).toBe(
      "Something new",
    );
  });
});
