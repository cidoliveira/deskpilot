from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, enum_column
from app.models.enums import TicketAction
from app.models.user import User


class TicketEvent(Base):
    """Append-only audit trail of a ticket. Rows are never updated or deleted.

    `old_value` / `new_value` hold the raw values (a status, a priority, or the id of
    the technician/category), so the history stays correct even if names change.
    """

    __tablename__ = "ticket_events"
    __table_args__ = (Index("ix_ticket_events_ticket_id_created_at", "ticket_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    action: Mapped[TicketAction] = mapped_column(enum_column(TicketAction, "ticket_action"))
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    changed_by: Mapped[User] = relationship()

    def __repr__(self) -> str:
        return f"<TicketEvent ticket={self.ticket_id} action={self.action}>"
