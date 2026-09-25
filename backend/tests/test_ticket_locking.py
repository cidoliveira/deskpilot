"""Row locking needs real, independent transactions, so these tests do not use the
rolled-back `db_session` fixture: they commit their own data and delete it at the end."""

import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError
from app.models import Category, Ticket, TicketEvent, User, UserRole
from app.schemas.ticket import TicketAssigneeUpdate
from app.services import ticket_workflow_service
from app.services.ticket_service import lock_ticket
from tests.factories import make_ticket, make_user


@dataclass(frozen=True)
class Scenario:
    ticket_id: int
    first_tech_id: int
    second_tech_id: int  # also the author, so the ticket stays visible to them


@pytest.fixture
def scenario(engine: Engine) -> Iterator[Scenario]:
    with Session(engine) as session:
        first = make_user(session, role=UserRole.TECHNICIAN)
        second = make_user(session, role=UserRole.TECHNICIAN)
        ticket = make_ticket(session, created_by=second)
        category_id = ticket.category_id
        data = Scenario(ticket.id, first.id, second.id)
        session.commit()
    yield data
    with Session(engine) as session:
        session.execute(delete(TicketEvent).where(TicketEvent.ticket_id == data.ticket_id))
        session.execute(delete(Ticket).where(Ticket.id == data.ticket_id))
        session.execute(delete(Category).where(Category.id == category_id))
        session.execute(delete(User).where(User.id.in_([data.first_tech_id, data.second_tech_id])))
        session.commit()


def _try_lock(session: Session, ticket_id: int) -> None:
    session.execute(select(Ticket).where(Ticket.id == ticket_id).with_for_update(nowait=True))


def test_locked_ticket_cannot_be_locked_by_another_transaction(
    engine: Engine, scenario: Scenario
) -> None:
    with Session(engine) as first, Session(engine) as second:
        lock_ticket(first, scenario.ticket_id, first.get(User, scenario.first_tech_id))

        # NOWAIT turns "wait for the lock" into an immediate error we can assert on.
        with pytest.raises(OperationalError, match="could not obtain lock"):
            _try_lock(second, scenario.ticket_id)
        second.rollback()

        first.rollback()  # releases the lock
        _try_lock(second, scenario.ticket_id)  # now it succeeds
        second.rollback()


def test_concurrent_claims_do_not_overwrite_each_other(engine: Engine, scenario: Scenario) -> None:
    """Two technicians claim the same ticket at the same time. The second one must wait
    for the first transaction, then see its committed assignment and get a 409."""
    outcome: dict[str, object] = {}

    def second_claim() -> None:
        with Session(engine, expire_on_commit=False) as session:
            tech = session.get(User, scenario.second_tech_id)
            # Load the ticket before the first claim commits: a stale copy in memory
            # that lock_ticket() must refresh (populate_existing).
            session.get(Ticket, scenario.ticket_id)
            outcome["started"] = True
            try:
                ticket_workflow_service.assign(
                    session,
                    scenario.ticket_id,
                    TicketAssigneeUpdate(assignee_id=tech.id),
                    tech,
                )
                outcome["result"] = "assigned"
            except AppError as exc:
                outcome["result"] = exc

    with Session(engine) as first:
        first_tech = first.get(User, scenario.first_tech_id)
        ticket = lock_ticket(first, scenario.ticket_id, first_tech)

        thread = threading.Thread(target=second_claim)
        thread.start()
        time.sleep(0.5)
        assert thread.is_alive(), "second claim should be waiting for the row lock"

        ticket.assigned_to_id = first_tech.id
        first.commit()  # releases the lock; the second claim continues

    thread.join(timeout=5)
    assert not thread.is_alive()
    assert isinstance(outcome["result"], ConflictError)
    assert outcome["result"].error == "ticket_already_assigned"
    with Session(engine) as check:
        assert check.get(Ticket, scenario.ticket_id).assigned_to_id == scenario.first_tech_id
