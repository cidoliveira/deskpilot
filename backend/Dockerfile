# Two targets from one file:
#   dev  - all dependencies (tests, linters), used by docker-compose.yml with auto-reload
#   prod - runtime dependencies only, used by docker-compose.prod.yml
FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /uvx /bin/

# The virtualenv lives outside /app so the dev bind mount (./backend:/app) does not hide it.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
RUN useradd --create-home --uid 1000 app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=2)"


FROM base AS dev

# Dependencies first, so this layer is cached while only the source code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
USER app
CMD ["sh", "-c", "alembic upgrade head && python -m app.scripts.create_admin && uvicorn app.main:app --host 0.0.0.0 --port 8000"]


FROM base AS prod

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
# Only what runs in production: no tests, no local files.
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
USER app
# Migrations run as a separate one-off step before the API starts (see
# docker-compose.prod.yml), so several API replicas never race to migrate.
# --forwarded-allow-ips trusts X-Forwarded-For from Nginx: the API port is only
# reachable inside the Compose network, never published directly.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
