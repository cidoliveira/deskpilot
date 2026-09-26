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

`check_transition()` diferencia três erros, nesta ordem:

| Situação | HTTP | `error` |
|---|---|---|
| Transição não existe na tabela (ex.: CLOSED → IN_PROGRESS) | 409 | `invalid_status_transition` |
| Transição existe, mas o usuário não é um ator permitido | 403 | `status_change_forbidden` |
| Falta técnico para IN_PROGRESS / WAITING_USER / RESOLVED | 422 | `ticket_not_assigned` |
| Resolver sem `resolution` | 422 | `resolution_required` |

Outras decisões do workflow:

- **Atribuir não muda o status.** Assumir o chamado e começar a trabalhar são ações separadas
  e explícitas; ambas ficam no histórico.
- **Reabrir** (RESOLVED → IN_PROGRESS) limpa `resolved_at`, mas mantém o texto da resolução
  anterior até a próxima resolução substituí-lo.
- **Concorrência:** toda mudança carrega o ticket com `SELECT ... FOR UPDATE`. Se dois técnicos
  tentam assumir o mesmo ticket ao mesmo tempo, o segundo espera o primeiro terminar, vê o
  ticket já atribuído e recebe `409 ticket_already_assigned` em vez de sobrescrever.
- **Atomicidade:** `history_service.record()` só adiciona o evento à sessão; o commit é feito
  junto com a mudança. Ou os dois são gravados, ou nenhum.
- **`allowed_actions`:** toda resposta de ticket individual traz `can_edit`, `can_claim`,
  `can_assign`, `can_change_priority` e `allowed_transitions`, calculados pela mesma política
  que valida as ações. O frontend só desenha os botões.

### Comentários

- Quem vê o ticket pode comentar, até ele ficar CLOSED ou CANCELLED (`409 ticket_closed`).
- O ticket é travado (`FOR UPDATE`) ao comentar, para um comentário não entrar enquanto outra
  requisição está fechando o chamado.
- **Regra automática:** se o ticket está em WAITING_USER e quem comenta é o autor, ele volta
  para IN_PROGRESS. É uma regra do sistema (não passa pela tabela de permissões manuais), mas
  fica no histórico como `STATUS_CHANGED` feito pelo autor.
- Comentários não são editados nem apagados, como numa conversa de suporte.
  **[PROD]** comentários internos, visíveis só para técnicos, e anexos.

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

- A visibilidade tem **uma única definição**, `ticket_policy.visible_to(user)`, um filtro SQL
  usado pela listagem, pelo detalhe e por toda ação sobre um ticket.
- Ticket que existe mas não é visível ao usuário retorna **404, não 403** (não revela existência).
- Ticket visível mas sem permissão para a ação retorna **403** (ex.: técnico editando um
  ticket disponível que ainda não assumiu).
- Atribuição concorrente usa `SELECT ... FOR UPDATE`; o segundo técnico recebe `409`.

### SLA

| Prioridade | Prazo de resolução |
|---|---|
| CRITICAL | 4 h |
| HIGH | 8 h |
| MEDIUM | 24 h |
| LOW | 48 h |

`sla_due_at = created_at + prazo`, gravado e indexado, recalculado a partir de `created_at`
quando a prioridade muda. O status é calculado na hora da consulta, nunca gravado:

| Status | Regra |
|---|---|
| `ON_TRACK` | aberto, menos de 80% da janela consumida |
| `AT_RISK` | aberto, 80% ou mais da janela consumida, ainda no prazo |
| `BREACHED` | aberto e vencido, **ou** resolvido depois do prazo |
| `MET` | resolvido dentro do prazo |
| `null` | CANCELLED (fora das métricas de SLA) |

A regra existe **duas vezes**: `sla_status()` em Python (para a resposta) e
`sla_status_condition()` em SQL (para o filtro `?sla_status=`). Um teste garante, para cada
status, que os tickets devolvidos pelo filtro SQL têm exatamente esse status calculado.

A migration que criou `sla_due_at` roda em três passos (coluna nula → backfill por
prioridade → NOT NULL), para funcionar numa tabela já populada.

### Listagem

- Filtros: `status` e `priority` (repetíveis), `category_id`, `assignee` (`me`, `none` ou id),
  `created_by_id`, `sla_status`, `q` (título/descrição), `created_from`/`created_to`
  (datas inclusivas, UTC).
- Os filtros são aplicados **depois** de `visible_to()`: só estreitam o resultado.
- `q` usa `ILIKE` com `%` e `_` escapados (casam literalmente).
- `sort` aceita só uma lista fixa de campos (`-` para decrescente); prioridade é ordenada por
  gravidade via `CASE`, e o id desempata para a paginação ser estável.

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

### Autenticação e autorização

- Login pelo fluxo OAuth2 *password* (form `username`/`password`), compatível com o Swagger.
- O token JWT carrega só `sub` (id do usuário), `iat` e `exp`. A role **não** vai no token:
  o usuário é recarregado do banco a cada request, então promoção, rebaixamento e
  desativação valem na hora.
- E-mail desconhecido e senha errada devolvem a mesma resposta (`invalid_credentials`), e
  o e-mail desconhecido ainda executa uma verificação de hash fictícia para o tempo de
  resposta não revelar quais e-mails existem.
- Conta inativa só recebe `403 user_inactive` depois de uma senha correta.
- O cadastro público rejeita campos extras (`role` inclusive): sem escalonamento de privilégio.
- Um admin não pode remover a própria role de admin nem se desativar.
- Política de senha por tamanho (8 a 128 caracteres), seguindo o NIST SP 800-63B.
- **Trade-off aceito:** `POST /auth/register` responde `409` para e-mail já cadastrado, o que
  permite descobrir e-mails existentes (o login não permite). Eliminar isso exige responder
  igual nos dois casos e avisar o dono do e-mail por mensagem, ou seja, envio de e-mail, que está
  fora do escopo. Em produção, com SSO, não haveria cadastro público.
- O script do admin inicial nunca promove uma conta existente: se alguém se cadastrar antes
  com o `FIRST_ADMIN_EMAIL`, o script registra um erro e não cria admin. No container, o script
  roda antes da API aceitar requisições, então isso não acontece no primeiro deploy.

### Frontend

| Decisão | Escolha | Motivo |
|---|---|---|
| Regras no cliente | Nenhuma: os botões vêm de `allowed_actions` | Uma única fonte de verdade (a política do backend) |
| Estado do servidor | TanStack Query, chaves centralizadas em `hooks/queries.ts` | Cache, loading e invalidação sem Redux |
| Sessão | Só o token é guardado; o usuário vem de `/auth/me` | Mesmo princípio do backend: role sempre atual |
| 401 autenticado | Desloga e limpa o cache | Nenhum dado da sessão anterior sobra na tela |
| Filtros | Na URL (`useListParams`), valores desconhecidos descartados | Links compartilháveis; URL editada não quebra a tela |
| Mensagens | Códigos de erro da API → PT-BR (`lib/errors.ts`) | O código é o contrato; o texto em inglês é só fallback |
| Erros de renderização | `errorElement` nas rotas | Tela de recuperação em vez de página em branco |
| Acessibilidade | Contraste AA, labels, skip link, `role="meter"` no SLA; axe no e2e | Verificado automaticamente, não só "no olho" |
| Telas de admin | Rotas lazy (chunks separados) | Usuários e técnicos não baixam esse código |

**Identidade visual.** Família IBM Plex (Condensed para títulos e rótulos de "painel", Mono
para códigos, horários e prazos). Um único acento (teal) para ações; vermelho, âmbar e verde
são **reservados para o SLA**, então cor sempre significa "tempo importa aqui". A peça
característica é o **medidor de SLA**: uma barra fina com quanto do prazo já foi consumido,
presente em cada linha da fila e, maior e com contagem regressiva, no detalhe do chamado.
Texto e marcas têm tons separados: as barras usam as cores vivas (3:1 bastam para gráficos) e
o texto usa versões escuras das mesmas cores (≥ 4,5:1).

### Produção

- `backend/Dockerfile` tem dois alvos: `dev` (todas as dependências, migrations no startup) e
  `prod` (só dependências de runtime, 2 workers do uvicorn atrás do proxy).
- `frontend/Dockerfile` gera o build com Node e serve com Nginx, que também faz proxy de
  `/api` para a API: frontend e API na **mesma origem**, sem CORS. Cache de um ano para os
  arquivos com hash, `no-cache` para o `index.html`, gzip e headers de segurança (CSP,
  `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`). A CSP estrita não é
  aplicada em `/api/` porque o Swagger UI carrega scripts próprios.
- `docker-compose.prod.yml`: `db` → `migrate` (roda uma vez) → `api` → `web`. A API só sobe se
  as migrations passarem; só o Nginx é publicado.
- **Limite de tentativas de login:** janela deslizante por (IP, e-mail); depois de 5 falhas em
  15 minutos, `429` com `Retry-After`. Por IP **e** e-mail para não permitir que um estranho
  bloqueie a conta de alguém a partir de outro lugar.
  O IP vem de um `X-Forwarded-For` que o Nginx **sobrescreve** (não concatena) e que o uvicorn só
  aceita vindo do endereço fixo do Nginx na rede interna. Sem isso, bastaria forjar o header a
  cada tentativa para ganhar tentativas infinitas (achado da revisão de segurança final; o CI
  agora testa exatamente esse ataque).
- O job *Production stack* do CI sobe essa pilha com o `.env.example` e faz um smoke test
  através do Nginx. Guia passo a passo em [deploy.md](deploy.md).

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
| Migrations | Em dev, no startup; em prod, serviço `migrate` separado (feito) | Etapa do pipeline de deploy, com aprovação |
| Imagem Docker | Alvos `dev` e `prod` (feito); rede interna, só Nginx publicado | + imagem assinada, scan de vulnerabilidades, registry privado |
| Observabilidade | logging padrão, healthchecks | Logs estruturados (JSON), métricas, tracing, alertas |
| Limite de login | Memória do processo (reinicia com a API, não é compartilhado entre workers) | Redis compartilhado ou rate limit no gateway/WAF |
| Tipos do frontend | Escritos à mão espelhando os schemas | Gerados do OpenAPI (ex.: `openapi-typescript`) |
| Validação das respostas | Confia no contrato (API do mesmo projeto, coberta por testes) | Validação na borda (Zod) se a API for de outro time |
| TLS | Fora do projeto (Caddy/Cloudflare na frente) | Terminação no load balancer, HSTS |
| E-mail único | Normalizado em minúsculas + UNIQUE | `citext` ou índice único em `lower(email)` |
| Admin inicial | Criado no startup a partir do `.env` | Provisionado pelo IdP / processo de onboarding |
| Senha | Tamanho mínimo | + verificação contra senhas vazadas (ex.: HIBP), MFA |
