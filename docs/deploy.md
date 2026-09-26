# Deploy

O repositório já traz tudo para rodar em produção com Docker. O CI sobe essa mesma pilha a
cada push (job *Production stack*) e testa, através do Nginx, o app, os headers de segurança,
o login do admin e as migrations — então os passos abaixo são os mesmos que o CI executa.

```
Internet ──HTTPS──▶ proxy com TLS ──▶ web (Nginx) ──/api──▶ api (FastAPI, 2 workers) ──▶ db
                                        └─ arquivos do React
```

Só o `web` é publicado. A API e o PostgreSQL ficam na rede interna do Compose.

## Opção 1 — VPS com Docker Compose (recomendada para o projeto)

Qualquer VPS Linux com 1 GB de RAM atende (DigitalOcean, Hetzner, Lightsail, Oracle Free Tier…).

### 1. Preparar o servidor

```bash
# Docker Engine + plugin compose (Ubuntu)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # sair e entrar de novo

git clone https://github.com/cidoliveira/deskpilot.git
cd deskpilot
```

### 2. Configurar o `.env`

```bash
cp .env.example .env
```

Troque **todos** os valores de exemplo. Para gerar segredos:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

| Variável | Em produção |
|---|---|
| `ENVIRONMENT` | já é forçado para `production` pelo `docker-compose.prod.yml` |
| `POSTGRES_PASSWORD` | segredo gerado, nunca o de exemplo |
| `JWT_SECRET_KEY` | segredo gerado (48+ caracteres). Trocar a chave desloga todo mundo |
| `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` | e-mail real e senha forte; troque a senha depois do primeiro acesso |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60 é razoável para uma ferramenta interna |
| `LOGIN_MAX_FAILURES` / `LOGIN_WINDOW_MINUTES` | 5 / 15 |
| `CORS_ORIGINS` | vazio (frontend e API na mesma origem, via Nginx) |
| `DEMO_PASSWORD` | remova: o seed de demonstração se recusa a rodar em produção |
| `WEB_PORT` | porta local do Nginx (ex.: `8080`, atrás do proxy com TLS) |

### 3. Subir

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
curl -f localhost:8080/api/v1/health
```

A ordem é garantida pelo Compose: `db` saudável → `migrate` (migrations + admin inicial,
roda uma vez e termina) → `api` → `web`. Se uma migration falha, a API nem sobe.

### 4. HTTPS

O Nginx do projeto fala HTTP na rede interna; o TLS fica num proxy na frente. O jeito mais
simples é o [Caddy](https://caddyserver.com), que emite e renova o certificado sozinho:

```
# /etc/caddy/Caddyfile
deskpilot.suaempresa.com.br {
    reverse_proxy localhost:8080
}
```

Alternativas: Cloudflare Tunnel (sem abrir portas) ou Traefik como mais um serviço do Compose.

**IP real do cliente atrás do proxy.** O Nginx do projeto **sobrescreve** o `X-Forwarded-For`
com o endereço de quem se conectou a ele (e a API só confia nesse header vindo do Nginx), para
que ninguém forje um IP e escape do limite de tentativas de login. Com um proxy de TLS na frente,
"quem se conectou" passa a ser o proxy, e todos os usuários parecem vir do mesmo IP. Para
recuperar o IP real, diga ao Nginx em quem confiar, no início de `conf.d/default.conf`:

```nginx
set_real_ip_from 172.17.0.1;      # endereço do proxy de TLS (ajuste ao seu ambiente)
real_ip_header X-Forwarded-For;
real_ip_recursive on;
```

Nunca use `set_real_ip_from 0.0.0.0/0`: isso volta a aceitar IP forjado por qualquer um.

### 5. Atualizar

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

O serviço `migrate` roda de novo e aplica só as migrations novas. As migrations do projeto
são reversíveis (`alembic downgrade -1`) e o CI testa ida e volta a cada push.

### 6. Backup do banco

```bash
# backup diário (crontab -e)
0 3 * * * cd /home/deploy/deskpilot && docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U deskpilot deskpilot | gzip > /backups/deskpilot-$(date +\%F).sql.gz

# restaurar
gunzip -c deskpilot-2026-09-26.sql.gz | docker compose -f docker-compose.prod.yml exec -T db \
  psql -U deskpilot deskpilot
```

Guarde os backups fora do servidor (bucket S3/R2, outro host) e teste a restauração de vez em
quando: backup que nunca foi restaurado é só esperança.

### 7. Monitorar

- `GET /healthz` (Nginx) e `GET /api/v1/health` (API + banco; responde 503 se o banco cair)
  servem para um monitor externo (UptimeRobot, Better Stack…).
- `docker compose -f docker-compose.prod.yml logs -f api` mostra os erros; o stack trace fica
  só no log, nunca na resposta da API.

## Opção 2 — Plataformas gerenciadas

Também funciona separando as partes:

- **API:** Render, Railway ou Fly.io a partir de `backend/Dockerfile` (target `prod`), com
  PostgreSQL gerenciado da própria plataforma. Rode `alembic upgrade head` como *release
  command* / *pre-deploy*, e `python -m app.scripts.create_admin` uma vez.
- **Frontend:** o `npm run build` gera arquivos estáticos (Vercel, Netlify, Cloudflare Pages).
  Como a API fica em outro domínio, configure `CORS_ORIGINS` com o domínio do frontend e faça
  o frontend chamar a URL completa da API (hoje ele usa `/api` na mesma origem).

## Checklist antes de abrir para usuários

- [ ] Todos os segredos do `.env` trocados (nenhum `change-me`)
- [ ] HTTPS ativo e HTTP redirecionando para HTTPS
- [ ] Senha do admin inicial trocada após o primeiro login
- [ ] Backup automático configurado **e** uma restauração testada
- [ ] Monitor externo apontando para `/api/v1/health`
- [ ] Cadastro público (`/auth/register`) desejado? Numa empresa real, contas vêm do SSO
