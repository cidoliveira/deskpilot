"""SQLAlchemy models.

Every model must be imported here so `Base.metadata` knows about it
(Alembic autogenerate relies on this).
"""

from app.db.base import Base

__all__ = ["Base"]
