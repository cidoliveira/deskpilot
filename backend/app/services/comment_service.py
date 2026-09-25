from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError
from app.models import TERMINAL_STATUSES, TicketComment, User
from app.schemas.comment import CommentCreate
from app.services.ticket_service import get_ticket, lock_ticket


def add_comment(
    session: Session, ticket_id: int, data: CommentCreate, author: User
) -> TicketComment:
    # Locked so a comment cannot slip in while another request is closing the ticket.
    ticket = lock_ticket(session, ticket_id, author)
    if ticket.status in TERMINAL_STATUSES:
        raise ConflictError(
            f"{ticket.status} tickets cannot receive comments", error="ticket_closed"
        )

    comment = TicketComment(ticket_id=ticket.id, author=author, message=data.message)
    session.add(comment)
    session.commit()
    session.refresh(comment)  # load created_at, set by the database
    return comment


def list_comments(session: Session, ticket_id: int, user: User) -> Sequence[TicketComment]:
    """Conversation of a visible ticket, oldest first."""
    ticket = get_ticket(session, ticket_id, user)
    return session.scalars(
        select(TicketComment)
        .where(TicketComment.ticket_id == ticket.id)
        .order_by(TicketComment.created_at, TicketComment.id)
        .options(selectinload(TicketComment.author))
    ).all()
