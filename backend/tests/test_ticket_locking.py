"""Row locking needs two real, independent transactions, so this test does not use the
rolled-back `db_session` fixture: it commits its own data and deletes it at the end."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import Category, Ticket, TicketEvent, User
from app.services.ticket_service import lock_ticket
from tests.factories import make_ticket, make_user


@pytest.fixture
def committed_ticket(engine: Engine) -> Iterator[tuple[int, int]]:
    with Session(engine) as session:
        author = make_user(session)
        ticket = make_ticket(session, created_by=author)
        ids = (ticket.id, author.id, ticket.category_id)
        session.commit()
    yield ids[0], ids[1]
    with Session(engine) as session:
        session.execute(delete(TicketEvent).where(TicketEvent.ticket_id == ids[0]))
        session.execute(delete(Ticket).where(Ticket.id == ids[0]))
        session.execute(delete(Category).where(Category.id == ids[2]))
        session.execute(delete(User).where(User.id == ids[1]))
        session.commit()


def _try_lock(session: Session, ticket_id: int) -> None:
    session.execute(select(Ticket).where(Ticket.id == ticket_id).with_for_update(nowait=True))


def test_locked_ticket_cannot_be_locked_by_another_transaction(
    engine: Engine, committed_ticket: tuple[int, int]
) -> None:
    ticket_id, author_id = committed_ticket

    with Session(engine) as first, Session(engine) as second:
        lock_ticket(first, ticket_id, first.get(User, author_id))

        # NOWAIT turns "wait for the lock" into an immediate error we can assert on.
        with pytest.raises(OperationalError, match="could not obtain lock"):
            _try_lock(second, ticket_id)
        second.rollback()

        first.rollback()  # releases the lock
        _try_lock(second, ticket_id)  # now it succeeds
        second.rollback()
