from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_is_never_stored_in_plain_text() -> None:
    hashed = hash_password("S3cure-password")

    assert hashed != "S3cure-password"
    assert hashed.startswith("$argon2")


def test_same_password_produces_different_hashes() -> None:
    # Random salt per hash: equal passwords are not detectable in the database.
    assert hash_password("S3cure-password") != hash_password("S3cure-password")


def test_verify_password() -> None:
    hashed = hash_password("S3cure-password")

    assert verify_password("S3cure-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_round_trip() -> None:
    token = create_access_token("42")

    assert decode_access_token(token) == "42"


def test_expired_token_is_rejected() -> None:
    long_ago = datetime.now(UTC) - timedelta(days=1)
    token = create_access_token("42", now=long_ago)

    with pytest.raises(UnauthorizedError) as exc_info:
        decode_access_token(token)
    assert exc_info.value.error == "token_expired"


def test_token_signed_with_another_key_is_rejected() -> None:
    now = datetime.now(UTC)
    forged = jwt.encode(
        {"sub": "1", "iat": now, "exp": now + timedelta(hours=1)},
        "attacker-key-that-is-long-enough-for-hs256",
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError) as exc_info:
        decode_access_token(forged)
    assert exc_info.value.error == "invalid_token"


def test_unsigned_token_is_rejected() -> None:
    now = datetime.now(UTC)
    unsigned = jwt.encode(
        {"sub": "1", "iat": now, "exp": now + timedelta(hours=1)}, key=None, algorithm="none"
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(unsigned)


def test_token_without_subject_is_rejected() -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {"iat": now, "exp": now + timedelta(hours=1)},
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(token)


def test_garbage_token_is_rejected() -> None:
    with pytest.raises(UnauthorizedError):
        decode_access_token("not-a-jwt")
