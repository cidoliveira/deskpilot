"""Create the first admin account from FIRST_ADMIN_* environment variables.

Usage: python -m app.scripts.create_admin

Idempotent: safe to run on every startup. An existing account is never modified.
"""

import logging
import sys

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.models import User, UserRole
from app.schemas.user import UserCreate
from app.services import user_service

logger = logging.getLogger("deskpilot.create_admin")


def ensure_first_admin(session: Session, settings: Settings) -> User | None:
    if not settings.first_admin_email or settings.first_admin_password is None:
        logger.info("FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD not set, skipping admin creation")
        return None

    existing = user_service.get_user_by_email(session, settings.first_admin_email)
    if existing is not None:
        if existing.role != UserRole.ADMIN:
            logger.warning("%s exists but is not an admin; leaving it unchanged", existing.email)
        else:
            logger.info("Admin %s already exists", existing.email)
        return existing

    admin = user_service.create_user(
        session,
        UserCreate(
            name=settings.first_admin_name,
            email=settings.first_admin_email,
            password=settings.first_admin_password.get_secret_value(),
            role=UserRole.ADMIN,
        ),
    )
    logger.info("Created admin %s", admin.email)
    return admin


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    try:
        with SessionLocal() as session:
            ensure_first_admin(session, get_settings())
    except ValidationError as exc:
        logger.error("Invalid FIRST_ADMIN_* settings: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
