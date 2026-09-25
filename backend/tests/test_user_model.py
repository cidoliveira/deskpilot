import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User, UserRole


def test_database_defaults_are_applied(db_session: Session) -> None:
    user = User(name="Ana", email="ana@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)

    assert user.role == UserRole.USER
    assert user.is_active is True
    assert user.created_at.tzinfo is not None
    assert user.updated_at is not None


def test_database_rejects_unknown_role(db_session: Session) -> None:
    # Defense in depth: even raw SQL cannot store an invalid role.
    with pytest.raises(IntegrityError, match="ck_users_user_role"), db_session.begin_nested():
        db_session.execute(
            text(
                "INSERT INTO users (name, email, password_hash, role) "
                "VALUES ('Eve', 'eve@example.com', 'x', 'SUPERUSER')"
            )
        )


def test_database_rejects_duplicate_email(db_session: Session) -> None:
    db_session.add(User(name="Ana", email="ana@example.com", password_hash="x"))
    db_session.flush()

    with pytest.raises(IntegrityError, match="uq_users_email"), db_session.begin_nested():
        db_session.add(User(name="Other Ana", email="ana@example.com", password_hash="y"))
        db_session.flush()
