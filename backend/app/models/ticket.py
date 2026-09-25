from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, enum_column
from app.models.category import Category
from app.models.enums import TicketPriority, TicketStatus
from app.models.user import User


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        # Defense in depth: the service validates this first with a friendly message,
        # the database guarantees no bug can store a resolved ticket without it.
        CheckConstraint(
            "status NOT IN ('RESOLVED', 'CLOSED') "
            "OR (resolution IS NOT NULL AND assigned_to_id IS NOT NULL)",
            name="resolution_required",
        ),
        Index("ix_tickets_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    priority: Mapped[TicketPriority] = mapped_column(
        enum_column(TicketPriority, "ticket_priority"),
        default=TicketPriority.MEDIUM,
        server_default=TicketPriority.MEDIUM,
        index=True,
    )
    status: Mapped[TicketStatus] = mapped_column(
        enum_column(TicketStatus, "ticket_status"),
        default=TicketStatus.OPEN,
        server_default=TicketStatus.OPEN,
        index=True,
    )
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    resolution: Mapped[str | None] = mapped_column(Text)
    # Stored (not computed on the fly) so "overdue" filters are a simple indexed comparison.
    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[Category] = relationship()
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    assigned_to: Mapped[User | None] = relationship(foreign_keys=[assigned_to_id])

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} status={self.status} priority={self.priority}>"
