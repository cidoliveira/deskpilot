from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Pagination
from app.api.ticket_params import TicketFilterParams
from app.models import Ticket, User
from app.schemas.common import Page
from app.schemas.history import TicketEventRead
from app.schemas.ticket import (
    TicketActionsRead,
    TicketAssigneeUpdate,
    TicketCreate,
    TicketDetail,
    TicketPriorityUpdate,
    TicketRead,
    TicketStatusUpdate,
    TicketSummary,
    TicketUpdate,
)
from app.services import ticket_service, ticket_workflow_service
from app.services.ticket_policy import allowed_actions
from app.services.ticket_queries import DEFAULT_SORT, SORT_FIELDS, SORT_PATTERN

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _detail(ticket: Ticket, user: User) -> TicketDetail:
    return TicketDetail(
        **TicketRead.model_validate(ticket).model_dump(),
        allowed_actions=TicketActionsRead.model_validate(allowed_actions(user, ticket)),
    )


@router.post("", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
def create_ticket(data: TicketCreate, db: DbSession, current_user: CurrentUser) -> TicketDetail:
    ticket = ticket_service.create_ticket(db, data, current_user)
    return _detail(ticket, current_user)


@router.get("", response_model=Page[TicketSummary])
def list_tickets(
    db: DbSession,
    current_user: CurrentUser,
    pagination: Pagination,
    filters: TicketFilterParams,
    sort: Annotated[
        str,
        Query(
            pattern=SORT_PATTERN,
            description=f"One of {', '.join(SORT_FIELDS)}; prefix with - for descending",
        ),
    ] = DEFAULT_SORT,
) -> Page[TicketSummary]:
    """Tickets visible to the current user (newest first unless `sort` is given).

    USER: own tickets. TECHNICIAN: available + assigned + own. ADMIN: all.
    """
    result = ticket_service.list_tickets(db, current_user, filters, pagination, sort)
    return Page[TicketSummary].model_validate(result)


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: int, db: DbSession, current_user: CurrentUser) -> TicketDetail:
    return _detail(ticket_service.get_ticket(db, ticket_id, current_user), current_user)


@router.patch("/{ticket_id}", response_model=TicketDetail)
def update_ticket(
    ticket_id: int, data: TicketUpdate, db: DbSession, current_user: CurrentUser
) -> TicketDetail:
    """Edit title, description or category.

    Author: only while OPEN. Assigned technician and admins: until the ticket is closed.
    """
    ticket = ticket_service.update_ticket(db, ticket_id, data, current_user)
    return _detail(ticket, current_user)


@router.get("/{ticket_id}/history", response_model=list[TicketEventRead])
def get_ticket_history(
    ticket_id: int, db: DbSession, current_user: CurrentUser
) -> list[TicketEventRead]:
    """Audit trail of the ticket, oldest first. Same visibility as the ticket itself."""
    entries = ticket_service.get_history(db, ticket_id, current_user)
    return [TicketEventRead.model_validate(entry) for entry in entries]


@router.patch("/{ticket_id}/status", response_model=TicketDetail)
def change_status(
    ticket_id: int, data: TicketStatusUpdate, db: DbSession, current_user: CurrentUser
) -> TicketDetail:
    """Move the ticket through the workflow. Send `resolution` when moving to RESOLVED.

    Invalid transition: 409. Wrong actor: 403. Missing assignee or resolution: 422.
    """
    ticket = ticket_workflow_service.change_status(db, ticket_id, data, current_user)
    return _detail(ticket, current_user)


@router.put("/{ticket_id}/assignee", response_model=TicketDetail)
def assign_ticket(
    ticket_id: int, data: TicketAssigneeUpdate, db: DbSession, current_user: CurrentUser
) -> TicketDetail:
    """Admins assign any active technician; technicians claim unassigned tickets
    (send their own id). Concurrent claims are serialized with a row lock."""
    ticket = ticket_workflow_service.assign(db, ticket_id, data, current_user)
    return _detail(ticket, current_user)


@router.patch("/{ticket_id}/priority", response_model=TicketDetail)
def change_priority(
    ticket_id: int, data: TicketPriorityUpdate, db: DbSession, current_user: CurrentUser
) -> TicketDetail:
    """Assigned technician or admin only."""
    ticket = ticket_workflow_service.change_priority(db, ticket_id, data, current_user)
    return _detail(ticket, current_user)
