import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TicketStatus, User, UserRole
from tests.factories import auth_headers, make_category, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


@pytest.fixture
def user(db_session: Session) -> User:
    return make_user(db_session)


@pytest.fixture
def tech(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.TECHNICIAN)


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.ADMIN)


def _patch(client: TestClient, ticket_id: int, user: User, payload: dict):
    return client.patch(f"{TICKETS_URL}/{ticket_id}", headers=auth_headers(user), json=payload)


def test_author_edits_open_ticket(client: TestClient, db_session: Session, user: User) -> None:
    ticket = make_ticket(db_session, created_by=user)
    new_category = make_category(db_session, name="Peripherals")

    response = _patch(
        client,
        ticket.id,
        user,
        {"title": "Mouse stopped working", "category_id": new_category.id},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["title"] == "Mouse stopped working"
    assert body["category"]["name"] == "Peripherals"
    assert body["description"] == ticket.description


def test_author_cannot_edit_ticket_in_progress(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=TicketStatus.IN_PROGRESS
    )

    response = _patch(client, ticket.id, user, {"title": "Changed my mind"})

    assert response.status_code == 403
    assert response.json()["error"] == "ticket_edit_forbidden"


def test_assigned_technician_edits_ticket(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=TicketStatus.WAITING_USER
    )

    response = _patch(client, ticket.id, tech, {"description": "Clarified: only on Wi-Fi."})

    assert response.status_code == 200
    assert response.json()["description"] == "Clarified: only on Wi-Fi."


def test_technician_cannot_edit_available_ticket(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)  # visible to tech, not assigned

    response = _patch(client, ticket.id, tech, {"title": "Hijacked title"})

    assert response.status_code == 403


def test_user_cannot_edit_ticket_of_another_user(
    client: TestClient, db_session: Session, user: User
) -> None:
    ticket = make_ticket(db_session, created_by=make_user(db_session))

    response = _patch(client, ticket.id, user, {"title": "Not my ticket"})

    assert response.status_code == 404


@pytest.mark.parametrize("status", [TicketStatus.CLOSED, TicketStatus.CANCELLED])
def test_terminal_tickets_cannot_be_edited_even_by_admin(
    client: TestClient,
    db_session: Session,
    user: User,
    tech: User,
    admin: User,
    status: TicketStatus,
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=status, resolution="Fixed"
    )

    response = _patch(client, ticket.id, admin, {"title": "Late correction"})

    assert response.status_code == 409
    assert response.json()["error"] == "ticket_closed"


def test_cannot_move_ticket_to_inactive_category(
    client: TestClient, db_session: Session, user: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)
    inactive = make_category(db_session, is_active=False)

    response = _patch(client, ticket.id, user, {"category_id": inactive.id})

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_category"


def test_ticket_keeps_its_category_after_it_is_deactivated(
    client: TestClient, db_session: Session, user: User
) -> None:
    category = make_category(db_session, name="Old System")
    ticket = make_ticket(db_session, created_by=user, category=category)
    category.is_active = False
    db_session.flush()

    response = _patch(client, ticket.id, user, {"title": "Still the old system"})

    assert response.status_code == 200
    assert response.json()["category"]["name"] == "Old System"


@pytest.mark.parametrize(
    "payload", [{"status": "RESOLVED"}, {"priority": "LOW"}, {"assigned_to_id": 1}]
)
def test_workflow_fields_are_not_editable_here(
    client: TestClient, db_session: Session, admin: User, payload: dict
) -> None:
    ticket = make_ticket(db_session, created_by=admin)

    response = _patch(client, ticket.id, admin, payload)

    assert response.status_code == 422


def test_title_cannot_be_null(client: TestClient, db_session: Session, user: User) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = _patch(client, ticket.id, user, {"title": None})

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_null_value"
