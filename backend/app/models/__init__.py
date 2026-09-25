"""SQLAlchemy models.

Every model must be imported here so `Base.metadata` knows about it
(Alembic autogenerate relies on this).
"""

from app.db.base import Base
from app.models.category import Category
from app.models.enums import (
    TERMINAL_STATUSES,
    TicketAction,
    TicketPriority,
    TicketStatus,
    UserRole,
)
from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent
from app.models.user import User

__all__ = [
    "TERMINAL_STATUSES",
    "Base",
    "Category",
    "Ticket",
    "TicketAction",
    "TicketEvent",
    "TicketPriority",
    "TicketStatus",
    "User",
    "UserRole",
]
