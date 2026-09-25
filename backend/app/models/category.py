from sqlalchemy import String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Category(TimestampMixin, Base):
    """Ticket category managed by admins (Hardware, Network, Access...)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    # Categories are deactivated, never deleted: old tickets keep their category,
    # but new tickets cannot use an inactive one.
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"
