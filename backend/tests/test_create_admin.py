import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import verify_password
from app.models import UserRole
from app.scripts.create_admin import ensure_first_admin
from tests.factories import make_user


def _settings(**overrides: object) -> Settings:
    return get_settings().model_copy(update=overrides)


def test_creates_admin_from_settings(db_session: Session) -> None:
    settings = _settings(
        first_admin_email="boss@example.com", first_admin_password=SecretStr("Str0ng-password")
    )

    admin = ensure_first_admin(db_session, settings)

    assert admin is not None
    assert admin.role == UserRole.ADMIN
    assert verify_password("Str0ng-password", admin.password_hash)


def test_is_idempotent(db_session: Session) -> None:
    settings = _settings(
        first_admin_email="boss@example.com", first_admin_password=SecretStr("Str0ng-password")
    )

    first = ensure_first_admin(db_session, settings)
    second = ensure_first_admin(db_session, settings)

    assert first is not None and second is not None
    assert first.id == second.id


def test_never_changes_existing_account(db_session: Session) -> None:
    existing = make_user(db_session, email="boss@example.com", role=UserRole.USER)
    settings = _settings(
        first_admin_email="boss@example.com", first_admin_password=SecretStr("Str0ng-password")
    )

    result = ensure_first_admin(db_session, settings)

    assert result is not None
    assert result.id == existing.id
    assert result.role == UserRole.USER


def test_skips_when_not_configured(db_session: Session) -> None:
    settings = _settings(first_admin_email=None, first_admin_password=None)

    assert ensure_first_admin(db_session, settings) is None


def test_rejects_weak_admin_password(db_session: Session) -> None:
    settings = _settings(
        first_admin_email="boss@example.com", first_admin_password=SecretStr("123")
    )

    with pytest.raises(ValidationError):
        ensure_first_admin(db_session, settings)
