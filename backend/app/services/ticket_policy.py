"""Who can see and do what with a ticket.

Kept separate from the service so the rules are easy to find, read and test.
"""

from sqlalchemy import ColumnElement, and_, or_, true

from app.models import Ticket, TicketStatus, User, UserRole


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
