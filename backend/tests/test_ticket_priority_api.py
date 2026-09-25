import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TicketPriority, TicketStatus, User, UserRole
from tests.factories import auth_headers, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


@pytest.fixture
def user(db_session: Session) -> User:
    return make_user(db_session)


@pytest.fixture
def tech(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.TECHNICIAN)


def _set_priority(client: TestClient, ticket_id: int, actor: User, priority: str):
    return client.patch(
        f"{TICKETS_URL}/{ticket_id}/priority",
        headers=auth_headers(actor),
        json={"priority": priority},
    )


def _history(client: TestClient, ticket_id: int, user: User) -> list[dict]:
    return client.get(f"{TICKETS_URL}/{ticket_id}/history", headers=auth_headers(user)).json()


def test_assigned_technician_changes_priority_and_it_is_recorded(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user, assigned_to=tech)

    response = _set_priority(client, ticket.id, tech, "CRITICAL")

    assert response.status_code == 200
    assert response.json()["priority"] == "CRITICAL"
    [event] = _history(client, ticket.id, tech)
    assert event["action"] == "PRIORITY_CHANGED"
    assert (event["old_value"], event["new_value"]) == ("MEDIUM", "CRITICAL")


def test_admin_changes_priority(client: TestClient, db_session: Session, user: User) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)
    ticket = make_ticket(db_session, created_by=user)

    response = _set_priority(client, ticket.id, admin, "LOW")

    assert response.json()["priority"] == "LOW"


def test_author_cannot_change_priority_after_creation(
    client: TestClient, db_session: Session, user: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = _set_priority(client, ticket.id, user, "CRITICAL")

    assert response.status_code == 403
    assert response.json()["error"] == "priority_change_forbidden"


def test_unassigned_technician_cannot_change_priority(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)  # available: visible, not theirs

    response = _set_priority(client, ticket.id, tech, "HIGH")

    assert response.status_code == 403


def test_closed_ticket_priority_cannot_change(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session,
        created_by=user,
        assigned_to=tech,
        status=TicketStatus.CLOSED,
        resolution="Fixed it.",
    )

    response = _set_priority(client, ticket.id, tech, "HIGH")

    assert response.status_code == 409


def test_closed_ticket_returns_409_before_checking_permission(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session,
        created_by=user,
        assigned_to=tech,
        status=TicketStatus.CLOSED,
        resolution="Fixed it.",
    )

    response = _set_priority(client, ticket.id, user, "HIGH")  # author: never allowed

    assert response.status_code == 409


def test_same_priority_records_nothing(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, priority=TicketPriority.HIGH
    )

    response = _set_priority(client, ticket.id, tech, "HIGH")

    assert response.status_code == 200
    assert _history(client, ticket.id, tech) == []
