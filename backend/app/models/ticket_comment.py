from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User


class TicketComment(Base):
    """Message on a ticket. Comments are not edited or deleted, like a support conversation."""

    __tablename__ = "ticket_comments"
    __table_args__ = (Index("ix_ticket_comments_ticket_id_created_at", "ticket_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped[User] = relationship()

    def __repr__(self) -> str:
        return f"<TicketComment id={self.id} ticket={self.ticket_id}>"
