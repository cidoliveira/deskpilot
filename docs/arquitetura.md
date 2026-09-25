# DeskPilot — Arquitetura e decisões

Documento vivo com o modelo de domínio, as regras de negócio e as decisões técnicas do projeto.
Marcação usada:

- **[P]** decisão tomada por simplicidade de portfólio
- **[PROD]** o que provavelmente seria diferente em um ambiente real

## 1. Visão geral

O núcleo do sistema é uma **máquina de estados de ticket com controle de acesso por role e
trilha de auditoria**. SLA, filtros, dashboard e frontend se apoiam nisso.

```
React (Vite)  ──HTTP/JSON──▶  FastAPI  ──SQLAlchemy──▶  PostgreSQL
                               │
                 api/ (rotas finas) → services/ (regras) → models/ (ORM)
```

- **Rotas** validam entrada (Pydantic), resolvem o usuário autenticado e chamam um service.
- **Services** concentram as regras de negócio e lançam exceções de domínio
  (`NotFoundError`, `ConflictError`...). Eles não conhecem HTTP.
- **Handlers** em `core/exceptions.py` convertem as exceções em respostas HTTP padronizadas.

## 2. Modelo de domínio

```
                 ┌──────────────┐
                 │   Category   │
                 └──────┬───────┘
                        │ 1:N
┌────────┐ created_by 1:N  ┌─────▼──────┐ 1:N ┌───────────────┐
│  User  │────────────────▶│   Ticket   │────▶│ TicketComment │
│        │ assigned_to 1:N │            │     └───────────────┘
│        │────────────────▶│            │ 1:N ┌───────────────┐
└────────┘  (opcional)     └────────────┘────▶│  TicketEvent  │
                                              └───────────────┘
```

### Enums

| Enum | Valores |
|---|---|
| UserRole | USER, TECHNICIAN, ADMIN |
| TicketStatus | OPEN, IN_PROGRESS, WAITING_USER, RESOLVED, CLOSED, CANCELLED |
| TicketPriority | LOW, MEDIUM, HIGH, CRITICAL |
| TicketAction | CREATED, ASSIGNED, STATUS_CHANGED, PRIORITY_CHANGED, CATEGORY_CHANGED, RESOLVED, CLOSED, REOPENED |
| SlaStatus (calculado) | ON_TRACK, AT_RISK, BREACHED, MET |

**Por que `CANCELLED`:** sem ele, um chamado duplicado ou aberto por engano teria de ser
"resolvido" com uma resolução falsa, poluindo métricas de SLA e tempo de resolução.

### Entidades

**User** — id, name, email (único, minúsculo), password_hash, role, is_active, created_at,
updated_at. Usuários são desativados, nunca deletados (preserva o histórico).

**Category** — id, name (único), description, is_active, created_at, updated_at.
Sem DELETE: categoria inativa não aceita tickets novos, mas permanece nos antigos.

**Ticket** — id, title, description, category_id, priority, status, created_by_id,
assigned_to_id, resolution, **sla_due_at**, created_at, updated_at, resolved_at, closed_at.
CHECK constraint: status RESOLVED/CLOSED exige `resolution` e `assigned_to_id`
(defesa em profundidade: o service valida primeiro com mensagem amigável).

**TicketComment** — id, ticket_id, author_id, message, created_at.
`is_internal` será adicionado depois, em migration própria.

**TicketEvent** — id, ticket_id, action, changed_by_id, old_value, new_value, created_at.
Append-only. Gravado pelo service **na mesma transação** da mudança.

## 3. Regras de negócio

### Máquina de estados

| De → Para | Quem | Condição | Evento |
|---|---|---|---|
| OPEN → IN_PROGRESS | responsável / admin | precisa ter responsável | STATUS_CHANGED |
| OPEN → CANCELLED | autor / admin | — | STATUS_CHANGED |
| IN_PROGRESS → WAITING_USER | responsável / admin | — | STATUS_CHANGED |
| WAITING_USER → IN_PROGRESS | responsável / admin, ou **automático** quando o autor comenta | — | STATUS_CHANGED |
| IN_PROGRESS → RESOLVED | responsável / admin | resolução obrigatória; grava `resolved_at` | RESOLVED |
| RESOLVED → CLOSED | autor / admin | grava `closed_at` | CLOSED |
| RESOLVED → IN_PROGRESS | autor / responsável / admin | limpa `resolved_at` | REOPENED |

CLOSED e CANCELLED são terminais. A tabela de transições é **dado** (`services/workflow.py`),
testada com testes unitários sem banco.

### Permissões

| Ação | USER | TECHNICIAN | ADMIN |
|---|---|---|---|
| Criar ticket | ✔ | ✔ | ✔ |
| Ver ticket | próprios | disponíveis (OPEN sem responsável) + atribuídos a ele + próprios | todos |
| Editar título/descrição/categoria | próprios, só em OPEN | atribuídos, exceto CLOSED | todos, exceto CLOSED |
| Assumir / atribuir | ✘ | a si mesmo, se sem responsável | qualquer técnico, reatribuir |
| Alterar prioridade | ✘ (só na criação) | atribuídos, exceto CLOSED | ✔ |
| Comentar | próprios, exceto CLOSED | visíveis, exceto CLOSED | ✔, exceto CLOSED |
| Usuários, categorias, métricas | ✘ | ✘ | ✔ |

- Ticket que existe mas não é visível ao usuário retorna **404, não 403** (não revela existência).
- Atribuição concorrente usa `SELECT ... FOR UPDATE`; o segundo técnico recebe `409`.

### SLA

| Prioridade | Prazo de resolução |
|---|---|
| CRITICAL | 4 h |
| HIGH | 8 h |
| MEDIUM | 24 h |
| LOW | 48 h |

`sla_due_at = created_at + prazo`, recalculado quando a prioridade muda. O status é calculado:
`AT_RISK` quando 80% da janela foi consumida; `MET`/`BREACHED` para tickets resolvidos
comparando `resolved_at`. Tickets CANCELLED não entram no SLA.

## 4. API

Prefixo `/api/v1`. Documentação interativa em `/api/v1/docs`.

| Método | Rota | Acesso |
|---|---|---|
| GET | `/health` | público |
| POST | `/auth/register` | público (cria apenas USER) |
| POST | `/auth/login` | público |
| GET | `/auth/me` | autenticado |
| GET, POST | `/users` | admin |
| GET, PATCH | `/users/{id}` | admin |
| GET, POST | `/tickets` | autenticado |
| GET, PATCH | `/tickets/{id}` | conforme permissões |
| PUT | `/tickets/{id}/assignee` | técnico / admin |
| PATCH | `/tickets/{id}/status` | conforme transições |
| PATCH | `/tickets/{id}/priority` | técnico / admin |
| GET, POST | `/tickets/{id}/comments` | visível |
| GET | `/tickets/{id}/history` | visível |
| GET, POST | `/categories` | GET autenticado / POST admin |
| PATCH | `/categories/{id}` | admin |
| GET | `/dashboard/metrics` | admin |

- Status, prioridade e responsável têm rotas próprias porque cada um tem permissões,
  validações e evento de histórico diferentes.
- O detalhe do ticket devolve `allowed_actions`, calculado pelo backend, para o frontend
  apenas desenhar os botões (regras não são duplicadas em TypeScript).

### Formato de erro

```json
{ "error": "invalid_status_transition", "message": "Cannot move ticket from CLOSED to IN_PROGRESS" }
{ "error": "validation_error", "message": "Invalid request", "details": [{ "field": "title", "message": "..." }] }
```

| Exceção | HTTP |
|---|---|
| NotFoundError | 404 |
| UnauthorizedError | 401 |
| PermissionDeniedError | 403 |
| ConflictError (transição inválida, ticket já atribuído, ticket fechado) | 409 |
| BusinessRuleError (resolução ausente...) | 422 |
| Erro inesperado | 500 genérico, stack trace só no log |

## 5. Decisões técnicas

| Decisão | Escolha | Motivo |
|---|---|---|
| ORM | SQLAlchemy 2 **síncrono** + psycopg 3 | Mais simples de estudar e testar; FastAPI roda rotas sync em threadpool |
| Hash de senha | pwdlib + Argon2 | Passlib está sem manutenção e quebra com bcrypt recente |
| JWT | PyJWT | Recomendado pela documentação atual do FastAPI |
| Role | Lida do banco a cada request, não do token | Mudança de role/desativação vale na hora |
| Enums no banco | VARCHAR + CHECK | ENUM nativo do Postgres é trabalhoso de evoluir com Alembic |
| Nomes de constraints | `naming_convention` no metadata | Migrations reproduzíveis |
| Histórico | Gravado no service | Explícito e testável (triggers seriam invisíveis no código) |
| Dados iniciais | Categorias via migration; admin/demo via script de seed | Categoria é dado de referência; demo não |
| Testes | Postgres real, migrations aplicadas via Alembic, rollback por teste | SQLite mascara diferenças; valida migrations |
| Pacotes | uv + pyproject.toml + uv.lock | Rápido e reprodutível |
| Frontend | TanStack Query + Context para auth | Não há estado global que justifique Redux |

## 6. Portfólio × produção

| Tema | [P] Aqui | [PROD] Em uma empresa |
|---|---|---|
| Identidade | Cadastro próprio + JWT | SSO / Entra ID / LDAP, sem auto-cadastro |
| Token | Só access token, em localStorage | Refresh token, cookie httpOnly + CSRF, revogação |
| SLA | Relógio 24x7, sem pausa | Calendário comercial, pausa em WAITING_USER, SLA de 1ª resposta |
| Busca | ILIKE | pg_trgm / full-text search |
| Paginação | offset/limit | keyset em grandes volumes |
| Prioridade | Escolhida pelo usuário | Matriz impacto × urgência |
| Fechamento | Manual | Auto-close agendado + pesquisa de satisfação |
| Migrations | Rodam no startup do container | Passo separado no pipeline de deploy |
| Imagem Docker | Única, com dependências de dev e reload | Multi-stage, sem dev deps, sem bind mount |
| Observabilidade | logging padrão | Logs estruturados, métricas, tracing, rate limit |
