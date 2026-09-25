from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.db.pagination import PageParams, PageResult, paginate
from app.models import TERMINAL_STATUSES, Ticket, TicketAction, User
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.schemas.ticket_filters import TicketFilters
from app.services import category_service, history_service, sla, ticket_queries
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
    now = datetime.now(UTC)
    ticket = Ticket(
        title=data.title,
        description=data.description,
        category=category,
        priority=data.priority,
        created_by=author,
        # Set explicitly so the SLA window starts exactly at the creation time.
        created_at=now,
        sla_due_at=sla.due_at(now, data.priority),
    )
    session.add(ticket)
    session.flush()  # assigns ticket.id, needed by the history event
    history_service.record(session, ticket, TicketAction.CREATED, author, new=ticket.status)
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


def lock_ticket(session: Session, ticket_id: int, user: User) -> Ticket:
    """Load a visible ticket with `SELECT ... FOR UPDATE`.

    The row stays locked until commit/rollback, so two concurrent changes to the same
    ticket (e.g. two technicians claiming it) run one after the other and the second one
    sees the first one's result instead of overwriting it.
    """
    stmt = (
        select(Ticket)
        .where(Ticket.id == ticket_id, visible_to(user))
        .with_for_update()
        # Refresh objects already in memory. SQLAlchemy 2 already implies this for FOR
        # UPDATE queries; it is kept explicit because correctness depends on it.
        .execution_options(populate_existing=True)
    )
    ticket = session.scalar(stmt)
    if ticket is None:
        raise NotFoundError("Ticket not found", error="ticket_not_found")
    return ticket


def ensure_not_terminal(ticket: Ticket) -> None:
    if ticket.status in TERMINAL_STATUSES:
        raise ConflictError(f"{ticket.status} tickets cannot be changed", error="ticket_closed")


def list_tickets(
    session: Session, user: User, filters: TicketFilters, params: PageParams
) -> PageResult[Ticket]:
    # Visibility first, filters on top: filters can only narrow what the user may see.
    stmt = select(Ticket).where(visible_to(user)).options(*_RELATIONS)
    stmt = ticket_queries.apply_filters(stmt, filters, user)
    stmt = stmt.order_by(Ticket.created_at.desc(), Ticket.id.desc())
    return paginate(session, stmt, params)


def update_ticket(session: Session, ticket_id: int, data: TicketUpdate, user: User) -> Ticket:
    ticket = lock_ticket(session, ticket_id, user)
    ensure_not_terminal(ticket)
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
        new_category = category_service.get_active_category(session, category_id)
        history_service.record(
            session,
            ticket,
            TicketAction.CATEGORY_CHANGED,
            user,
            old=ticket.category_id,
            new=new_category.id,
        )
        ticket.category = new_category

    for field, value in changes.items():
        setattr(ticket, field, value)
    session.commit()
    return get_ticket(session, ticket.id, user)


def get_history(session: Session, ticket_id: int, user: User) -> list[history_service.HistoryEntry]:
    ticket = get_ticket(session, ticket_id, user)
    return history_service.list_history(session, ticket)
