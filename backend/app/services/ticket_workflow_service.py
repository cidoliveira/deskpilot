"""Workflow operations on a ticket: status, assignee and priority.

Every operation follows the same steps inside one transaction:
lock the row -> validate the rules -> record the history event -> apply -> commit.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, PermissionDeniedError
from app.models import Ticket, TicketAction, TicketStatus, User, UserRole
from app.schemas.ticket import TicketAssigneeUpdate, TicketStatusUpdate
from app.services import history_service, workflow
from app.services.ticket_policy import can_be_assigned
from app.services.ticket_service import ensure_not_terminal, get_ticket, lock_ticket


def change_status(session: Session, ticket_id: int, data: TicketStatusUpdate, user: User) -> Ticket:
    ticket = lock_ticket(session, ticket_id, user)
    source, target = ticket.status, data.status
    workflow.check_transition(user, ticket, target)

    now = datetime.now(UTC)
    if target == TicketStatus.RESOLVED:
        if not data.resolution:
            raise BusinessRuleError(
                "A resolution is required to resolve a ticket", error="resolution_required"
            )
        ticket.resolution = data.resolution
        ticket.resolved_at = now
    elif data.resolution is not None:
        raise BusinessRuleError(
            "A resolution can only be sent when resolving the ticket",
            error="unexpected_resolution",
        )

    if target in {TicketStatus.CLOSED, TicketStatus.CANCELLED}:
        ticket.closed_at = now
    if source == TicketStatus.RESOLVED and target == TicketStatus.IN_PROGRESS:
        # Reopened: the previous resolution text is kept until the next one replaces it.
        ticket.resolved_at = None

    history_service.record(
        session, ticket, workflow.event_action(source, target), user, old=source, new=target
    )
    ticket.status = target
    session.commit()
    return get_ticket(session, ticket.id, user)


def assign(session: Session, ticket_id: int, data: TicketAssigneeUpdate, user: User) -> Ticket:
    """Admins assign any technician; a technician can only claim an unassigned ticket."""
    if user.role == UserRole.USER:
        raise PermissionDeniedError("Only staff can assign tickets", error="assignment_forbidden")

    ticket = lock_ticket(session, ticket_id, user)
    ensure_not_terminal(ticket)

    assignee = session.get(User, data.assignee_id)
    if assignee is None or not can_be_assigned(assignee):
        raise BusinessRuleError(
            "The assignee must be an active technician or admin", error="invalid_assignee"
        )

    if user.role == UserRole.TECHNICIAN:
        if assignee.id != user.id:
            raise PermissionDeniedError(
                "Technicians can only assign tickets to themselves", error="assignment_forbidden"
            )
        if ticket.assigned_to_id not in (None, user.id):
            raise ConflictError(
                "Ticket is already assigned to another technician",
                error="ticket_already_assigned",
            )

    if ticket.assigned_to_id != assignee.id:
        history_service.record(
            session, ticket, TicketAction.ASSIGNED, user, old=ticket.assigned_to_id, new=assignee.id
        )
        ticket.assigned_to = assignee
    session.commit()  # also releases the row lock when nothing changed
    return get_ticket(session, ticket.id, user)
