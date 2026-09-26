from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Ticket, TicketComment, TicketEvent, TicketStatus, User
from app.scripts.seed_demo import DEMO_TICKETS, DEMO_USERS, seed


def test_seed_creates_demo_data_through_the_workflow(db_session: Session) -> None:
    seed(db_session, "Str0ng-password")

    emails = {email for _, email, _ in DEMO_USERS}
    users = db_session.scalars(select(User).where(User.email.in_(emails))).all()
    statuses = Counter(db_session.scalars(select(Ticket.status)))

    assert len(users) == len(DEMO_USERS)
    assert statuses == Counter(demo.status for demo in DEMO_TICKETS)
    assert statuses[TicketStatus.CLOSED] > 0
    # Real workflow: history events and comments exist, not just rows with a status.
    assert db_session.scalar(select(func.count()).select_from(TicketEvent)) > len(DEMO_TICKETS)
    assert db_session.scalar(select(func.count()).select_from(TicketComment)) > 0


def test_events_happen_after_ticket_creation(db_session: Session) -> None:
    seed(db_session, "Str0ng-password")

    rows = db_session.execute(
        select(Ticket.created_at, TicketEvent.created_at).join(
            TicketEvent, TicketEvent.ticket_id == Ticket.id
        )
    ).all()

    assert all(event_at >= created_at for created_at, event_at in rows)


def test_seed_is_idempotent(db_session: Session) -> None:
    seed(db_session, "Str0ng-password")
    seed(db_session, "Str0ng-password")

    assert db_session.scalar(select(func.count()).select_from(Ticket)) == len(DEMO_TICKETS)


def test_last_update_matches_the_last_activity(db_session: Session) -> None:
    seed(db_session, "Str0ng-password")

    # Every demo ticket was created at least 1 h "ago": its last activity is in the past,
    # not the moment the seed ran.
    ten_minutes_ago = datetime.now(UTC) - timedelta(minutes=10)
    for ticket in db_session.scalars(select(Ticket)):
        assert ticket.created_at <= ticket.updated_at <= ten_minutes_ago
