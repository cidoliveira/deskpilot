"""SQL building blocks for the ticket list: filters (and, later, ordering)."""

from sqlalchemy import Select

from app.models import Ticket, User
from app.schemas.ticket_filters import TicketFilters


def apply_filters(stmt: Select, filters: TicketFilters, user: User) -> Select:
    if filters.status:
        stmt = stmt.where(Ticket.status.in_(filters.status))
    if filters.priority:
        stmt = stmt.where(Ticket.priority.in_(filters.priority))
    if filters.category_id is not None:
        stmt = stmt.where(Ticket.category_id == filters.category_id)
    if filters.created_by_id is not None:
        stmt = stmt.where(Ticket.created_by_id == filters.created_by_id)

    if filters.assignee == "me":
        stmt = stmt.where(Ticket.assigned_to_id == user.id)
    elif filters.assignee == "none":
        stmt = stmt.where(Ticket.assigned_to_id.is_(None))
    elif filters.assignee is not None:
        stmt = stmt.where(Ticket.assigned_to_id == int(filters.assignee))
    return stmt
