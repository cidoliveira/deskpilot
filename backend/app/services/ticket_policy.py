"""Who can see and do what with a ticket.

Kept separate from the service so the rules are easy to find, read and test.
"""

from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_, or_, true

from app.models import TERMINAL_STATUSES, Ticket, TicketStatus, User, UserRole
from app.services import workflow


def visible_to(user: User) -> ColumnElement[bool]:
    """SQL filter with the tickets `user` may see. The single definition of visibility:
    listing, detail and every action on a ticket go through it.

    - ADMIN: every ticket
    - TECHNICIAN: available tickets (OPEN and unassigned), tickets assigned to them
      and tickets they opened
    - USER: only tickets they opened
    """
    if user.role == UserRole.ADMIN:
        return true()

    own = Ticket.created_by_id == user.id
    if user.role == UserRole.TECHNICIAN:
        available = and_(Ticket.assigned_to_id.is_(None), Ticket.status == TicketStatus.OPEN)
        return or_(own, available, Ticket.assigned_to_id == user.id)
    return own


def can_edit(user: User, ticket: Ticket) -> bool:
    """Whether `user` may edit title, description and category.

    Terminal tickets (CLOSED/CANCELLED) are rejected before this check, for everyone.
    - ADMIN: any ticket
    - assigned technician: their tickets
    - author: only while the ticket is still OPEN (nobody is working on it yet)
    """
    if user.role == UserRole.ADMIN or ticket.assigned_to_id == user.id:
        return True
    return ticket.created_by_id == user.id and ticket.status == TicketStatus.OPEN


def can_change_priority(user: User, ticket: Ticket) -> bool:
    """Admins, or the technician working on the ticket (users only choose it on creation)."""
    return user.role == UserRole.ADMIN or ticket.assigned_to_id == user.id


def can_be_assigned(user: User) -> bool:
    """Only active staff can be responsible for a ticket."""
    return user.is_active and user.role in {UserRole.TECHNICIAN, UserRole.ADMIN}


@dataclass(frozen=True)
class TicketActions:
    """What `user` can do with a ticket right now. The frontend only renders these flags,
    so the rules live in one place (here) instead of being duplicated in TypeScript."""

    can_edit: bool
    can_claim: bool
    can_assign: bool
    can_change_priority: bool
    can_comment: bool
    allowed_transitions: list[TicketStatus]


def allowed_actions(user: User, ticket: Ticket) -> TicketActions:
    active = ticket.status not in TERMINAL_STATUSES
    return TicketActions(
        can_edit=active and can_edit(user, ticket),
        can_claim=active and user.role == UserRole.TECHNICIAN and ticket.assigned_to_id is None,
        can_assign=active and user.role == UserRole.ADMIN,
        can_change_priority=active and can_change_priority(user, ticket),
        # Anyone who can see the ticket may comment until it is closed.
        can_comment=active,
        allowed_transitions=workflow.allowed_transitions(user, ticket),
    )
