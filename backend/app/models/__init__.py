"""SQLAlchemy models.

Every model must be imported here so `Base.metadata` knows about it
(Alembic autogenerate relies on this).
"""

from app.db.base import Base
from app.models.enums import UserRole
from app.models.user import User

__all__ = ["Base", "User", "UserRole"]
