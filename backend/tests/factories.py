"""Small helpers to create test data directly in the database."""

from itertools import count

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models import User, UserRole

DEFAULT_PASSWORD = "Str0ng-password"
# Hashing is intentionally slow (Argon2); hash the default password only once.
_DEFAULT_PASSWORD_HASH = hash_password(DEFAULT_PASSWORD)
_sequence = count(1)


def make_user(
    session: Session,
    *,
    role: UserRole = UserRole.USER,
    email: str | None = None,
    name: str | None = None,
    password: str = DEFAULT_PASSWORD,
    is_active: bool = True,
) -> User:
    number = next(_sequence)
    password_hash = (
        _DEFAULT_PASSWORD_HASH if password == DEFAULT_PASSWORD else hash_password(password)
    )
    user = User(
        name=name or f"{role.value.title()} {number}",
        email=email or f"{role.value.lower()}{number}@example.com",
        password_hash=password_hash,
        role=role,
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    return user


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
