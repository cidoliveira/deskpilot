import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TicketStatus, User, UserRole
from tests.factories import auth_headers, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


@pytest.fixture
def user(db_session: Session) -> User:
    return make_user(db_session)


@pytest.fixture
def tech(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.TECHNICIAN, name="Carla Tech")


@pytest.fixture
def other_tech(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.TECHNICIAN, name="Diego Tech")


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.ADMIN)


def _assign(client: TestClient, ticket_id: int, actor: User, assignee_id: int):
    return client.put(
        f"{TICKETS_URL}/{ticket_id}/assignee",
        headers=auth_headers(actor),
        json={"assignee_id": assignee_id},
    )


def _history(client: TestClient, ticket_id: int, user: User) -> list[dict]:
    return client.get(f"{TICKETS_URL}/{ticket_id}/history", headers=auth_headers(user)).json()


def test_technician_claims_available_ticket(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = _assign(client, ticket.id, tech, tech.id)

    assert response.status_code == 200
    assert response.json()["assigned_to"] == {"id": tech.id, "name": "Carla Tech"}
    assert response.json()["status"] == "OPEN"  # assigning does not start the work


def test_assignment_is_recorded_in_history(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)

    _assign(client, ticket.id, tech, tech.id)

    [event] = _history(client, ticket.id, user)
    assert event["action"] == "ASSIGNED"
    assert event["old_value"] is None
    assert (event["new_value"], event["new_label"]) == (str(tech.id), "Carla Tech")


def test_claimed_ticket_is_no_longer_available_to_other_technicians(
    client: TestClient, db_session: Session, user: User, tech: User, other_tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)
    _assign(client, ticket.id, tech, tech.id)

    response = _assign(client, ticket.id, other_tech, other_tech.id)

    assert response.status_code == 404  # it left the "available" queue


def test_technician_cannot_take_ticket_from_another_technician(
    client: TestClient, db_session: Session, tech: User, other_tech: User
) -> None:
    # Visible to `tech` because they opened it, but someone else is working on it.
    ticket = make_ticket(db_session, created_by=tech, assigned_to=other_tech)

    response = _assign(client, ticket.id, tech, tech.id)

    assert response.status_code == 409
    assert response.json()["error"] == "ticket_already_assigned"


def test_technician_cannot_assign_someone_else(
    client: TestClient, db_session: Session, user: User, tech: User, other_tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = _assign(client, ticket.id, tech, other_tech.id)

    assert response.status_code == 403


def test_regular_user_cannot_assign(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = _assign(client, ticket.id, user, tech.id)

    assert response.status_code == 403
    assert response.json()["error"] == "assignment_forbidden"


def test_admin_reassigns_ticket(
    client: TestClient,
    db_session: Session,
    user: User,
    tech: User,
    other_tech: User,
    admin: User,
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=TicketStatus.IN_PROGRESS
    )

    response = _assign(client, ticket.id, admin, other_tech.id)

    assert response.json()["assigned_to"]["id"] == other_tech.id
    [event] = _history(client, ticket.id, admin)
    assert (event["old_label"], event["new_label"]) == ("Carla Tech", "Diego Tech")


@pytest.mark.parametrize("kind", ["regular_user", "inactive_tech", "missing"])
def test_assignee_must_be_active_staff(
    client: TestClient, db_session: Session, user: User, admin: User, kind: str
) -> None:
    ticket = make_ticket(db_session, created_by=user)
    assignee_id = {
        "regular_user": lambda: make_user(db_session).id,
        "inactive_tech": lambda: (
            make_user(db_session, role=UserRole.TECHNICIAN, is_active=False).id
        ),
        "missing": lambda: 999999,
    }[kind]()

    response = _assign(client, ticket.id, admin, assignee_id)

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_assignee"


@pytest.mark.parametrize("status", [TicketStatus.CLOSED, TicketStatus.CANCELLED])
def test_terminal_ticket_cannot_be_assigned(
    client: TestClient,
    db_session: Session,
    user: User,
    tech: User,
    other_tech: User,
    admin: User,
    status: TicketStatus,
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=status, resolution="Fixed it."
    )

    response = _assign(client, ticket.id, admin, other_tech.id)

    assert response.status_code == 409
    assert response.json()["error"] == "ticket_closed"


def test_assigning_same_technician_again_records_nothing(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user, assigned_to=tech)

    response = _assign(client, ticket.id, tech, tech.id)

    assert response.status_code == 200
    assert _history(client, ticket.id, tech) == []
