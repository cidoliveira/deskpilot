from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TicketPriority, TicketStatus, User, UserRole
from tests.factories import auth_headers, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.ADMIN)


def _order(client: TestClient, user: User, sort: str | None = None) -> list[int]:
    params = {"sort": sort} if sort else {}
    response = client.get(TICKETS_URL, headers=auth_headers(user), params=params)
    assert response.status_code == 200, response.json()
    return [ticket["id"] for ticket in response.json()["items"]]


def test_default_order_is_newest_first(
    client: TestClient, db_session: Session, admin: User
) -> None:
    now = datetime.now(UTC)
    old = make_ticket(db_session, created_by=admin, created_at=now - timedelta(days=2))
    new = make_ticket(db_session, created_by=admin, created_at=now)

    assert _order(client, admin) == [new.id, old.id]
    assert _order(client, admin, "created_at") == [old.id, new.id]


def test_priority_is_sorted_by_severity_not_alphabetically(
    client: TestClient, db_session: Session, admin: User
) -> None:
    by_priority = {
        p: make_ticket(db_session, created_by=admin, priority=p).id for p in TicketPriority
    }
    severity = [
        TicketPriority.CRITICAL,
        TicketPriority.HIGH,
        TicketPriority.MEDIUM,
        TicketPriority.LOW,
    ]

    assert _order(client, admin, "-priority") == [by_priority[p] for p in severity]
    assert _order(client, admin, "priority") == [by_priority[p] for p in reversed(severity)]


def test_sort_by_sla_due_date_shows_most_urgent_first(
    client: TestClient, db_session: Session, admin: User
) -> None:
    low = make_ticket(db_session, created_by=admin, priority=TicketPriority.LOW)
    critical = make_ticket(db_session, created_by=admin, priority=TicketPriority.CRITICAL)

    assert _order(client, admin, "sla_due_at") == [critical.id, low.id]


def test_sla_sort_puts_finished_tickets_after_running_ones(
    client: TestClient, db_session: Session, admin: User
) -> None:
    long_ago = datetime.now(UTC) - timedelta(days=5)
    closed = make_ticket(
        db_session,
        created_by=admin,
        assigned_to=admin,
        status=TicketStatus.CLOSED,
        resolution="Done.",
        created_at=long_ago,
        resolved_at=long_ago + timedelta(hours=1),
    )
    cancelled = make_ticket(
        db_session, created_by=admin, status=TicketStatus.CANCELLED, created_at=long_ago
    )
    running = make_ticket(db_session, created_by=admin, priority=TicketPriority.LOW)

    # The finished tickets have the oldest due dates, but no urgency left.
    assert _order(client, admin, "sla_due_at")[0] == running.id
    assert set(_order(client, admin, "sla_due_at")[1:]) == {closed.id, cancelled.id}


def test_sort_by_title(client: TestClient, db_session: Session, admin: User) -> None:
    b = make_ticket(db_session, created_by=admin, title="Backup failed")
    a = make_ticket(db_session, created_by=admin, title="Access denied")

    assert _order(client, admin, "title") == [a.id, b.id]


@pytest.mark.parametrize("sort", ["password_hash", "created_at; DROP TABLE tickets", "--title"])
def test_unknown_sort_fields_are_rejected(client: TestClient, admin: User, sort: str) -> None:
    response = client.get(TICKETS_URL, headers=auth_headers(admin), params={"sort": sort})

    assert response.status_code == 422
