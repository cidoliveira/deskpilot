"""Workflow operations on a ticket: status, assignee and priority.

Every operation follows the same steps inside one transaction:
lock the row -> validate the rules -> record the history event -> apply -> commit.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.models import Ticket, TicketStatus, User
from app.schemas.ticket import TicketStatusUpdate
from app.services import history_service, workflow
from app.services.ticket_service import get_ticket, lock_ticket


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
