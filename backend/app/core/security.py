"""Password hashing (Argon2) and JWT access tokens."""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

_password_hash = PasswordHash.recommended()  # Argon2id

# Hash of a random value, used to spend the same time on logins for unknown e-mails,
# so response time does not reveal which e-mails are registered.
_DUMMY_HASH = _password_hash.hash("deskpilot-timing-protection")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def spend_password_verification_time() -> None:
    _password_hash.verify("not-the-password", _DUMMY_HASH)


def create_access_token(subject: str, *, now: datetime | None = None) -> str:
    settings = get_settings()
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> str:
    """Return the token subject (user id), or raise UnauthorizedError."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired", error="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid token", error="invalid_token") from exc
    return str(payload["sub"])
