import { ApiError } from "../services/http";

// The API's `error` codes are a stable contract; its English `message` is a fallback.
const MESSAGES: Record<string, string> = {
  invalid_credentials: "E-mail ou senha incorretos.",
  user_inactive: "Sua conta está desativada. Procure o administrador.",
  token_expired: "Sua sessão expirou. Entre novamente.",
  too_many_requests: "Muitas tentativas seguidas. Aguarde alguns minutos e tente de novo.",
  email_already_registered: "Já existe uma conta com este e-mail.",
  permission_denied: "Você não tem permissão para esta ação.",
  ticket_not_found: "Chamado não encontrado.",
  ticket_closed: "Este chamado já foi encerrado e não pode ser alterado.",
  ticket_edit_forbidden: "Você não pode editar este chamado agora.",
  invalid_status_transition: "Essa mudança de status não é permitida.",
  status_change_forbidden: "Você não pode mover este chamado para esse status.",
  ticket_not_assigned: "Atribua um técnico antes de iniciar o atendimento.",
  resolution_required: "Descreva a solução para resolver o chamado.",
  ticket_already_assigned: "Outro técnico já assumiu este chamado.",
  assignment_forbidden: "Você não pode atribuir este chamado.",
  invalid_assignee: "Escolha um técnico ou administrador ativo.",
  priority_change_forbidden: "Só o técnico responsável ou um administrador muda a prioridade.",
  invalid_category: "Escolha uma categoria ativa.",
  category_name_taken: "Já existe uma categoria com esse nome.",
  cannot_change_own_role: "Você não pode remover o seu próprio acesso de administrador.",
  cannot_deactivate_self: "Você não pode desativar a sua própria conta.",
  validation_error: "Revise os campos destacados.",
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return MESSAGES[error.code] ?? error.message;
  if (error instanceof Error) return error.message;
  return "Algo deu errado. Tente novamente.";
}
