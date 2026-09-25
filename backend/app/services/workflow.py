"""Ticket status state machine.

The allowed transitions are *data* (the TRANSITIONS table), not a chain of ifs, so the
whole workflow can be read in one place and tested without a database.

    OPEN ──────────▶ IN_PROGRESS ◀────────▶ WAITING_USER
     │                  │    ▲
     ▼                  ▼    │ (reopen)
   CANCELLED          RESOLVED ──────────▶ CLOSED
"""

from enum import StrEnum

from app.core.exceptions import BusinessRuleError, ConflictError, PermissionDeniedError
from app.models import Ticket, TicketAction, TicketStatus, User, UserRole


class Actor(StrEnum):
    """How a user relates to a ticket, which decides what they may do with it."""

    AUTHOR = "AUTHOR"
    ASSIGNEE = "ASSIGNEE"
    ADMIN = "ADMIN"


_S = TicketStatus
TRANSITIONS: dict[tuple[TicketStatus, TicketStatus], frozenset[Actor]] = {
    (_S.OPEN, _S.IN_PROGRESS): frozenset({Actor.ASSIGNEE, Actor.ADMIN}),
    (_S.OPEN, _S.CANCELLED): frozenset({Actor.AUTHOR, Actor.ADMIN}),
    (_S.IN_PROGRESS, _S.WAITING_USER): frozenset({Actor.ASSIGNEE, Actor.ADMIN}),
    (_S.WAITING_USER, _S.IN_PROGRESS): frozenset({Actor.ASSIGNEE, Actor.ADMIN}),
    (_S.IN_PROGRESS, _S.RESOLVED): frozenset({Actor.ASSIGNEE, Actor.ADMIN}),
    (_S.RESOLVED, _S.CLOSED): frozenset({Actor.AUTHOR, Actor.ADMIN}),
    (_S.RESOLVED, _S.IN_PROGRESS): frozenset({Actor.AUTHOR, Actor.ASSIGNEE, Actor.ADMIN}),
}

# Someone must be working on the ticket to reach these states.
REQUIRES_ASSIGNEE = frozenset({_S.IN_PROGRESS, _S.WAITING_USER, _S.RESOLVED})


def actors(user: User, ticket: Ticket) -> frozenset[Actor]:
    found = set()
    if ticket.created_by_id == user.id:
        found.add(Actor.AUTHOR)
    # Only staff can be assigned, so ASSIGNEE implies TECHNICIAN or ADMIN: this is what
    # guarantees that only technicians/admins can resolve tickets.
    if ticket.assigned_to_id == user.id:
        found.add(Actor.ASSIGNEE)
    if user.role == UserRole.ADMIN:
        found.add(Actor.ADMIN)
    return frozenset(found)


def allowed_transitions(user: User, ticket: Ticket) -> list[TicketStatus]:
    """Target statuses `user` may move the ticket to right now (used by the UI)."""
    user_actors = actors(user, ticket)
    return [
        target
        for (source, target), allowed in TRANSITIONS.items()
        if source == ticket.status
        and user_actors & allowed
        and (target not in REQUIRES_ASSIGNEE or ticket.assigned_to_id is not None)
    ]


def check_transition(user: User, ticket: Ticket, target: TicketStatus) -> None:
    """Raise if `user` cannot move `ticket` to `target`. The order of the checks matters:
    first "does this transition exist at all", then "who may do it", then preconditions."""
    allowed = TRANSITIONS.get((ticket.status, target))
    if allowed is None:
        raise ConflictError(
            f"Cannot move ticket from {ticket.status} to {target}",
            error="invalid_status_transition",
        )
    if not actors(user, ticket) & allowed:
        raise PermissionDeniedError(
            f"You cannot move this ticket from {ticket.status} to {target}",
            error="status_change_forbidden",
        )
    if target in REQUIRES_ASSIGNEE and ticket.assigned_to_id is None:
        raise BusinessRuleError(
            "Assign a technician before starting work on the ticket",
            error="ticket_not_assigned",
        )


def event_action(source: TicketStatus, target: TicketStatus) -> TicketAction:
    """History action for a transition: specific actions make the timeline readable."""
    if target == _S.RESOLVED:
        return TicketAction.RESOLVED
    if target == _S.CLOSED:
        return TicketAction.CLOSED
    if source == _S.RESOLVED and target == _S.IN_PROGRESS:
        return TicketAction.REOPENED
    return TicketAction.STATUS_CHANGED
