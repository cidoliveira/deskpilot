# DeskPilot

[![CI](https://github.com/cidoliveira/deskpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/cidoliveira/deskpilot/actions/workflows/ci.yml)

> Sistema de **Help Desk / Service Desk** para gestão de chamados internos de TI.
> API REST em FastAPI + PostgreSQL, com frontend React (em desenvolvimento).

🇺🇸 *An IT Help Desk / Service Desk web app for internal tickets: FastAPI REST API with
role-based access, auditable ticket history, SLA tracking and a React frontend.*

---

## O problema

Em muitas empresas, pedidos de suporte chegam por e-mail, chat e corredor. Nada fica registrado,
ninguém sabe quem está cuidando do quê e não há como medir tempo de atendimento.
O DeskPilot centraliza os chamados em um fluxo único e auditável:

- o **usuário** abre e acompanha seus chamados;
- o **técnico** assume, trabalha e resolve;
- o **administrador** distribui a fila, gerencia usuários e categorias e acompanha métricas e SLA.

## Funcionalidades

| Status | Funcionalidade |
|---|---|
| ✅ | Estrutura da API, Docker Compose, PostgreSQL, migrations (Alembic), tratamento de erros padronizado |
| ✅ | Autenticação JWT, senhas com Argon2 e controle de acesso por role (USER, TECHNICIAN, ADMIN) |
| ✅ | Gestão de usuários pelo administrador, com paginação e filtros |
| ✅ | Categorias gerenciáveis pelo admin (7 categorias padrão criadas por migration) |
| ✅ | Abertura, listagem paginada, detalhe e edição de tickets com visibilidade por role |
| ✅ | Máquina de estados de status, atribuição (com trava de concorrência), prioridade |
| ✅ | Histórico auditável de todas as mudanças, gravado na mesma transação |
| ✅ | `allowed_actions`: a API informa ao frontend o que o usuário pode fazer em cada ticket |
| ✅ | Comentários, bloqueados em tickets encerrados; a resposta do autor retoma um ticket em WAITING_USER |
| ✅ | SLA por prioridade (no prazo, em risco, violado, cumprido) |
| ✅ | Filtros (status, prioridade, categoria, técnico, autor, SLA, período), busca textual e ordenação |
| ✅ | Dashboard de métricas: volume, SLA, tempo médio de resolução e carga por técnico |
| ✅ | CI no GitHub Actions: lint, validação de migrations e testes com cobertura mínima de 90% |
| ⏳ | Frontend React |

## Arquitetura

```
backend/
├── app/
│   ├── main.py          # criação da aplicação
│   ├── api/             # rotas HTTP (finas) e dependências
│   ├── core/            # configuração, segurança, exceções
│   ├── db/              # engine, sessão, base declarativa
│   ├── models/          # modelos SQLAlchemy
│   ├── schemas/         # schemas Pydantic (entrada/saída)
│   └── services/        # regras de negócio
├── alembic/             # migrations
└── tests/
```

As regras de negócio ficam na camada de **services**, que não conhece HTTP: ela lança exceções
de domínio, convertidas em respostas padronizadas por handlers centrais.
Modelo de domínio, regras e decisões técnicas estão em **[docs/arquitetura.md](docs/arquitetura.md)**.

## Tecnologias

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, PostgreSQL 17
- **Testes:** Pytest, HTTPX (TestClient), banco PostgreSQL real e isolado
- **Qualidade:** Ruff (lint + format)
- **Infra:** Docker, Docker Compose, uv (gerenciador de pacotes)
- **Frontend (planejado):** React, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query

## Como executar

Pré-requisitos: Docker e Docker Compose.

```bash
cp .env.example .env        # ajuste POSTGRES_PASSWORD
docker compose up --build
```

- API: http://localhost:8000/api/v1/health
- Swagger (OpenAPI): http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

Ao subir, o container da API aplica as migrations e cria o admin inicial definido em
`FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` (se ainda não existir).

### Autenticação

1. Crie uma conta em `POST /api/v1/auth/register` (sempre com role `USER`)
   ou entre com o admin inicial.
2. Faça login em `POST /api/v1/auth/login` (form OAuth2: `username` = e-mail, `password`).
3. Envie o token no header `Authorization: Bearer <token>`.

No Swagger, o botão **Authorize** faz o login direto pela interface.
Técnicos e administradores são criados por um admin em `POST /api/v1/users`.

### Configuração (.env)

| Variável | Descrição | Padrão |
|---|---|---|
| `ENVIRONMENT` | `development`, `test` ou `production` | `development` |
| `LOG_LEVEL` | Nível de log | `INFO` |
| `API_PORT` | Porta da API no host | `8000` |
| `POSTGRES_HOST` | Host do banco (`db` dentro do Compose) | `localhost` |
| `POSTGRES_PORT` | Porta do banco | `5432` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | Credenciais do banco | — (obrigatórias) |
| `POSTGRES_DB` | Banco da aplicação | `deskpilot` |
| `POSTGRES_TEST_DB` | Banco usado pelos testes (precisa terminar em `_test`) | `deskpilot_test` |
| `JWT_SECRET_KEY` | Chave de assinatura dos tokens (mínimo 32 caracteres) | — (obrigatória) |
| `JWT_ALGORITHM` | Algoritmo do JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token | `60` |
| `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` | Admin criado no startup, se ainda não existir | opcional |
| `FIRST_ADMIN_NAME` | Nome do admin inicial | `Administrator` |

O arquivo `.env` nunca é versionado; apenas `.env.example`.

## Migrations

```bash
# criar uma migration a partir dos modelos
docker compose exec api alembic revision --autogenerate -m "descricao"

# aplicar / reverter
docker compose exec api alembic upgrade head
docker compose exec api alembic downgrade -1

# verificar se os modelos estão sincronizados com as migrations
docker compose exec api alembic check
```

## Testes

Mais de 280 testes, com cobertura acima de 95%. Não testam só o caminho feliz; cobrem as
regras de negócio, por exemplo:

- usuário não enxerga ticket de outro usuário (404) e filtros nunca ampliam a visibilidade;
- transições de status inválidas (409), ator errado (403), resolução sem texto ou sem técnico (422);
- ticket fechado não aceita comentários nem edição;
- toda atribuição, mudança de status e de prioridade gera evento no histórico;
- dois técnicos assumindo o mesmo ticket ao mesmo tempo (duas transações reais);
- a regra de SLA em SQL (filtros e dashboard) concorda com a regra em Python (respostas);
- constraints do banco rejeitam dados inválidos mesmo inseridos por SQL direto.

Os testes usam um banco PostgreSQL separado (`POSTGRES_TEST_DB`), criado automaticamente.
O schema é montado **rodando as migrations**, o que também as valida, e cada teste roda em
uma transação desfeita ao final.

```bash
# dentro do Docker
docker compose exec api pytest

# ou localmente (com o banco do Compose rodando)
cd backend
uv sync
uv run pytest --cov
```

## Exemplos de uso

```bash
# chamados do técnico logado, em andamento, mais urgentes primeiro
GET /api/v1/tickets?assignee=me&status=IN_PROGRESS&sort=-priority

# chamados abertos fora do SLA
GET /api/v1/tickets?sla_status=BREACHED&status=OPEN&status=IN_PROGRESS

# busca textual em março
GET /api/v1/tickets?q=vpn&created_from=2026-03-01&created_to=2026-03-31
```

## Documentação da API

Gerada automaticamente pelo FastAPI (OpenAPI 3) em `/api/v1/docs`.
Todos os erros seguem o mesmo formato:

```json
{ "error": "invalid_status_transition", "message": "Cannot move ticket from CLOSED to IN_PROGRESS" }
```

## Screenshots

*Em breve, junto com o frontend.*

## Roadmap

- [x] **Etapa 1:** FastAPI, Docker, PostgreSQL, SQLAlchemy, Alembic, tratamento de erros
- [x] **Etapa 2:** usuários, autenticação JWT, roles
- [x] **Etapa 3:** categorias e tickets (visibilidade por role, paginação)
- [x] **Etapa 4:** workflow (atribuição, status, prioridade) e histórico
- [x] **Etapa 5:** comentários
- [x] **Etapa 6:** SLA, filtros, busca e ordenação
- [x] **Etapa 7:** dashboard de métricas e CI (GitHub Actions)
- [ ] **Etapa 8:** frontend React
- [ ] **Etapa 9:** deploy
