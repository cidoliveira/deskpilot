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
