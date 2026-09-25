"""Test infrastructure.

- Tests run against a real PostgreSQL database (`POSTGRES_TEST_DB`), never SQLite,
  so constraints, ILIKE, time zones and row locks behave like production.
- The schema is created by running the Alembic migrations, which validates them too.
- Each test runs inside a transaction that is rolled back at the end, so tests are
  isolated and fast. Service code can still call `commit()`: the session is bound with
  `join_transaction_mode="create_savepoint"`, so commits only release a savepoint.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings
from app.db.session import get_db
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _ensure_test_database() -> None:
    settings = get_settings()
    name = settings.postgres_test_db
    # Safety net: never run the destructive test setup against a non-test database.
    if not name.endswith("_test") or name == settings.postgres_db:
        raise RuntimeError(f"Refusing to use {name!r} as test database (must end with '_test')")

    admin_engine = create_engine(settings.maintenance_database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name})
        if not exists:
            quoted = conn.dialect.identifier_preparer.quote(name)
            conn.execute(text(f"CREATE DATABASE {quoted}"))
    admin_engine.dispose()


def _run_migrations(engine: Engine) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    with engine.begin() as conn:
        # Start from an empty schema so every run exercises the full migration chain.
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
        config.attributes["connection"] = conn
        command.upgrade(config, "head")


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    _ensure_test_database()
    test_engine = create_engine(get_settings().test_database_url)
    _run_migrations(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def app(db_session: Session):
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    return application


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
