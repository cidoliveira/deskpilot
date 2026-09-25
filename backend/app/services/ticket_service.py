from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.db.pagination import PageParams, PageResult, paginate
from app.models import TERMINAL_STATUSES, Ticket, User
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services import category_service
from app.services.ticket_policy import can_edit, visible_to

# Load the related rows used by the response schemas in a fixed number of queries
# (avoids one query per ticket when listing: the N+1 problem).
_RELATIONS = (
    selectinload(Ticket.category),
    selectinload(Ticket.created_by),
    selectinload(Ticket.assigned_to),
)


def create_ticket(session: Session, data: TicketCreate, author: User) -> Ticket:
    category = category_service.get_active_category(session, data.category_id)
    ticket = Ticket(
        title=data.title,
        description=data.description,
        category=category,
        priority=data.priority,
        created_by=author,
    )
    session.add(ticket)
    session.commit()
    return get_ticket(session, ticket.id, author)


def get_ticket(session: Session, ticket_id: int, user: User) -> Ticket:
    """Ticket visible to `user`. A ticket that exists but is not visible returns 404 as
    well, so users cannot discover other people's tickets by guessing ids."""
    stmt = select(Ticket).where(Ticket.id == ticket_id, visible_to(user)).options(*_RELATIONS)
    ticket = session.scalar(stmt)
    if ticket is None:
        raise NotFoundError("Ticket not found", error="ticket_not_found")
    return ticket


def list_tickets(session: Session, user: User, params: PageParams) -> PageResult[Ticket]:
    stmt = (
        select(Ticket)
        .where(visible_to(user))
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .options(*_RELATIONS)
    )
    return paginate(session, stmt, params)


def update_ticket(session: Session, ticket_id: int, data: TicketUpdate, user: User) -> Ticket:
    ticket = get_ticket(session, ticket_id, user)
    if ticket.status in TERMINAL_STATUSES:
        raise ConflictError(f"{ticket.status} tickets cannot be edited", error="ticket_closed")
    if not can_edit(user, ticket):
        raise PermissionDeniedError("You cannot edit this ticket", error="ticket_edit_forbidden")

    changes = data.model_dump(exclude_unset=True)
    null_fields = [field for field, value in changes.items() if value is None]
    if null_fields:
        raise BusinessRuleError(
            f"Fields cannot be null: {', '.join(null_fields)}", error="invalid_null_value"
        )

    category_id = changes.pop("category_id", None)
    if category_id is not None and category_id != ticket.category_id:
        ticket.category = category_service.get_active_category(session, category_id)

    for field, value in changes.items():
        setattr(ticket, field, value)
    session.commit()
    return get_ticket(session, ticket.id, user)
