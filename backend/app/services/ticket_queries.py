"""SQL building blocks for the ticket list: filters and ordering."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Select, and_, case, or_

from app.models import Ticket, TicketPriority, TicketStatus, User
from app.schemas.ticket_filters import TicketFilters
from app.services import sla

# Priority sorted by severity, not alphabetically (VARCHAR column).
_PRIORITY_RANK = case(
    {
        TicketPriority.LOW: 1,
        TicketPriority.MEDIUM: 2,
        TicketPriority.HIGH: 3,
        TicketPriority.CRITICAL: 4,
    },
    value=Ticket.priority,
)

# Whitelist: only these fields can be used to sort (never raw user input in ORDER BY).
SORT_FIELDS = {
    "created_at": Ticket.created_at,
    "updated_at": Ticket.updated_at,
    "sla_due_at": Ticket.sla_due_at,
    "priority": _PRIORITY_RANK,
    "title": Ticket.title,
}
SORT_PATTERN = rf"^-?({'|'.join(SORT_FIELDS)})$"
DEFAULT_SORT = "-created_at"


def start_of_day(day: date) -> datetime:
    """Midnight UTC of `day` (date filters are interpreted in UTC)."""
    return datetime.combine(day, time.min, tzinfo=UTC)


def _contains(text: str) -> str:
    """ILIKE pattern that matches `text` literally (% and _ in user input are not wildcards)."""
    escaped = text.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    return f"%{escaped}%"


def apply_filters(stmt: Select, filters: TicketFilters, user: User, now: datetime) -> Select:
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

    if filters.q:
        pattern = _contains(filters.q)
        stmt = stmt.where(
            or_(
                Ticket.title.ilike(pattern, escape="\\"),
                Ticket.description.ilike(pattern, escape="\\"),
            )
        )
    if filters.sla_status is not None:
        stmt = stmt.where(sla.sla_status_condition(filters.sla_status, now))
    if filters.created_from is not None:
        stmt = stmt.where(Ticket.created_at >= start_of_day(filters.created_from))
    if filters.created_to is not None:
        # Inclusive end date: everything before the start of the next day.
        stmt = stmt.where(Ticket.created_at < start_of_day(filters.created_to + timedelta(days=1)))
    return stmt


# Tickets whose SLA clock is still running (not resolved, not cancelled) come first.
_CLOCK_STOPPED = case(
    (and_(Ticket.resolved_at.is_(None), Ticket.status != TicketStatus.CANCELLED), 0), else_=1
)


def apply_sort(stmt: Select, sort: str) -> Select:
    """`field` ascending, `-field` descending. The id breaks ties so pages are stable.

    Sorting by SLA due date means "most urgent first": finished tickets have old due dates
    but no urgency, so they go after every ticket whose clock is still running.
    """
    field = sort.removeprefix("-")
    descending = sort.startswith("-")
    column = SORT_FIELDS[field]
    order = [column.desc(), Ticket.id.desc()] if descending else [column.asc(), Ticket.id.asc()]
    if field == "sla_due_at":
        order.insert(0, _CLOCK_STOPPED.asc())
    return stmt.order_by(*order)
