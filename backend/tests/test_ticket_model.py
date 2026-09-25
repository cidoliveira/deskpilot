import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import TicketPriority, TicketStatus, UserRole
from tests.factories import make_category, make_ticket, make_user


def test_new_ticket_defaults(db_session: Session) -> None:
    author = make_user(db_session)
    ticket = make_ticket(db_session, created_by=author)
    db_session.refresh(ticket)

    assert ticket.status == TicketStatus.OPEN
    assert ticket.priority == TicketPriority.MEDIUM
    assert ticket.assigned_to_id is None
    assert ticket.created_at.tzinfo is not None


@pytest.mark.parametrize("status", [TicketStatus.RESOLVED, TicketStatus.CLOSED])
def test_database_requires_resolution_and_technician(
    db_session: Session, status: TicketStatus
) -> None:
    author = make_user(db_session)
    tech = make_user(db_session, role=UserRole.TECHNICIAN)

    def violation():
        return pytest.raises(IntegrityError, match="ck_tickets_resolution_required")

    with violation(), db_session.begin_nested():
        make_ticket(db_session, created_by=author, status=status, assigned_to=tech)

    with violation(), db_session.begin_nested():
        make_ticket(db_session, created_by=author, status=status, resolution="Fixed")


def test_resolved_ticket_with_technician_and_resolution_is_valid(db_session: Session) -> None:
    author = make_user(db_session)
    tech = make_user(db_session, role=UserRole.TECHNICIAN)

    ticket = make_ticket(
        db_session,
        created_by=author,
        status=TicketStatus.RESOLVED,
        assigned_to=tech,
        resolution="Replaced the network cable.",
    )

    assert ticket.id is not None


def test_database_rejects_unknown_status(db_session: Session) -> None:
    author = make_user(db_session)
    category = make_category(db_session)

    with pytest.raises(IntegrityError, match="ck_tickets_ticket_status"), db_session.begin_nested():
        db_session.execute(
            text(
                "INSERT INTO tickets (title, description, category_id, created_by_id, status) "
                "VALUES ('t', 'd', :category, :author, 'DONE')"
            ),
            {"category": category.id, "author": author.id},
        )
