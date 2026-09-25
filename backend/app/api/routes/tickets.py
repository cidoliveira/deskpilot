from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, Pagination
from app.schemas.common import Page
from app.schemas.history import TicketEventRead
from app.schemas.ticket import (
    TicketAssigneeUpdate,
    TicketCreate,
    TicketRead,
    TicketStatusUpdate,
    TicketSummary,
    TicketUpdate,
)
from app.services import ticket_service, ticket_workflow_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(data: TicketCreate, db: DbSession, current_user: CurrentUser) -> TicketRead:
    ticket = ticket_service.create_ticket(db, data, current_user)
    return TicketRead.model_validate(ticket)


@router.get("", response_model=Page[TicketSummary])
def list_tickets(
    db: DbSession, current_user: CurrentUser, pagination: Pagination
) -> Page[TicketSummary]:
    """Tickets visible to the current user, newest first.

    USER: own tickets. TECHNICIAN: available + assigned + own. ADMIN: all.
    """
    result = ticket_service.list_tickets(db, current_user, pagination)
    return Page[TicketSummary].model_validate(result)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: int, db: DbSession, current_user: CurrentUser) -> TicketRead:
    return TicketRead.model_validate(ticket_service.get_ticket(db, ticket_id, current_user))


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: int, data: TicketUpdate, db: DbSession, current_user: CurrentUser
) -> TicketRead:
    """Edit title, description or category.

    Author: only while OPEN. Assigned technician and admins: until the ticket is closed.
    """
    ticket = ticket_service.update_ticket(db, ticket_id, data, current_user)
    return TicketRead.model_validate(ticket)


@router.get("/{ticket_id}/history", response_model=list[TicketEventRead])
def get_ticket_history(
    ticket_id: int, db: DbSession, current_user: CurrentUser
) -> list[TicketEventRead]:
    """Audit trail of the ticket, oldest first. Same visibility as the ticket itself."""
    entries = ticket_service.get_history(db, ticket_id, current_user)
    return [TicketEventRead.model_validate(entry) for entry in entries]


@router.patch("/{ticket_id}/status", response_model=TicketRead)
def change_status(
    ticket_id: int, data: TicketStatusUpdate, db: DbSession, current_user: CurrentUser
) -> TicketRead:
    """Move the ticket through the workflow. Send `resolution` when moving to RESOLVED.

    Invalid transition: 409. Wrong actor: 403. Missing assignee or resolution: 422.
    """
    ticket = ticket_workflow_service.change_status(db, ticket_id, data, current_user)
    return TicketRead.model_validate(ticket)


@router.put("/{ticket_id}/assignee", response_model=TicketRead)
def assign_ticket(
    ticket_id: int, data: TicketAssigneeUpdate, db: DbSession, current_user: CurrentUser
) -> TicketRead:
    """Admins assign any active technician; technicians claim unassigned tickets
    (send their own id). Concurrent claims are serialized with a row lock."""
    ticket = ticket_workflow_service.assign(db, ticket_id, data, current_user)
    return TicketRead.model_validate(ticket)
