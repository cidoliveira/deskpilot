from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    spend_password_verification_time,
    verify_password,
)
from app.models import User
from app.schemas.auth import TokenRead
from app.services.login_throttle import LoginThrottle
from app.services.user_service import get_user_by_email

_settings = get_settings()
login_throttle = LoginThrottle(
    max_failures=_settings.login_max_failures,
    window_seconds=_settings.login_window_minutes * 60,
)


def _invalid_credentials() -> UnauthorizedError:
    # Same message for unknown e-mail and wrong password: do not reveal which e-mails exist.
    return UnauthorizedError("Incorrect e-mail or password", error="invalid_credentials")


def authenticate(session: Session, email: str, password: str) -> User:
    user = get_user_by_email(session, email)
    if user is None:
        spend_password_verification_time()
        raise _invalid_credentials()
    if not verify_password(password, user.password_hash):
        raise _invalid_credentials()
    # Checked only after the password, so this does not leak account status to strangers.
    if not user.is_active:
        raise PermissionDeniedError("User account is inactive", error="user_inactive")
    return user


def login(session: Session, email: str, password: str, *, client: str) -> TokenRead:
    """`client` identifies the caller (its IP) for brute-force protection."""
    key = f"{client}|{email.strip().lower()}"
    login_throttle.check(key)
    try:
        user = authenticate(session, email, password)
    except UnauthorizedError:
        login_throttle.record_failure(key)
        raise
    login_throttle.reset(key)
    settings = get_settings()
    return TokenRead(
        access_token=create_access_token(str(user.id)),
        expires_in=settings.access_token_expire_minutes * 60,
    )


def get_user_from_token(session: Session, token: str) -> User:
    """Resolve the token owner. The user is always reloaded from the database, so a role
    change or deactivation takes effect immediately, without waiting for the token to expire."""
    subject = decode_access_token(token)
    user = session.get(User, int(subject)) if subject.isdigit() else None
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid token", error="invalid_token")
    return user
