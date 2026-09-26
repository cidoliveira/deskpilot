export interface FieldDetail {
  field: string;
  message: string;
  type?: string;
  ctx?: Record<string, number | string>;
}

/**
 * PT-BR message for one API validation error. Uses the stable `type` and the limits in
 * `ctx`; unknown types fall back to the API's (English) message.
 */
export function fieldMessage(detail: FieldDetail): string {
  const ctx = detail.ctx ?? {};
  switch (detail.type) {
    case "missing":
      return "Preencha este campo.";
    case "string_too_short":
      return Number(ctx.min_length) <= 1
        ? "Preencha este campo."
        : `Use pelo menos ${ctx.min_length} caracteres.`;
    case "string_too_long":
      return `Use no máximo ${ctx.max_length} caracteres.`;
    case "value_error":
      return detail.field.endsWith("email")
        ? "Informe um e-mail válido, como nome@empresa.com."
        : detail.message;
    case "extra_forbidden":
      return "Este campo não pode ser enviado.";
    case "int_parsing":
    case "enum":
    case "literal_error":
      return "Escolha um valor válido.";
    default:
      return detail.message;
  }
}
