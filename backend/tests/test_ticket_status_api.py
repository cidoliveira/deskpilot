import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TicketStatus, User, UserRole
from tests.factories import auth_headers, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"
RESOLUTION = "Replaced the faulty network cable."


@pytest.fixture
def user(db_session: Session) -> User:
    return make_user(db_session)


@pytest.fixture
def tech(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.TECHNICIAN)


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.ADMIN)


def _set_status(client: TestClient, ticket_id: int, user: User, status: str, **extra: str):
    return client.patch(
        f"{TICKETS_URL}/{ticket_id}/status",
        headers=auth_headers(user),
        json={"status": status, **extra},
    )


def _actions(client: TestClient, ticket_id: int, user: User) -> list[str]:
    history = client.get(f"{TICKETS_URL}/{ticket_id}/history", headers=auth_headers(user))
    return [event["action"] for event in history.json()]


def test_full_lifecycle_is_recorded_in_history(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user, assigned_to=tech)

    steps = [
        (tech, "IN_PROGRESS", {}),
        (tech, "WAITING_USER", {}),
        (tech, "IN_PROGRESS", {}),
        (tech, "RESOLVED", {"resolution": RESOLUTION}),
        (user, "CLOSED", {}),
    ]
    for actor, status, extra in steps:
        response = _set_status(client, ticket.id, actor, status, **extra)
        assert response.status_code == 200, response.json()
        assert response.json()["status"] == status

    body = response.json()
    assert body["resolution"] == RESOLUTION
    assert body["resolved_at"] is not None
    assert body["closed_at"] is not None
    assert _actions(client, ticket.id, user) == [
        "STATUS_CHANGED",
        "STATUS_CHANGED",
        "STATUS_CHANGED",
        "RESOLVED",
        "CLOSED",
    ]


def test_status_event_keeps_old_and_new_values(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user, assigned_to=tech)

    _set_status(client, ticket.id, tech, "IN_PROGRESS")

    history = client.get(f"{TICKETS_URL}/{ticket.id}/history", headers=auth_headers(tech))
    [event] = history.json()
    assert (event["old_value"], event["new_value"]) == ("OPEN", "IN_PROGRESS")
    assert event["changed_by"]["id"] == tech.id


def test_resolving_requires_a_resolution(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=TicketStatus.IN_PROGRESS
    )

    response = _set_status(client, ticket.id, tech, "RESOLVED")

    assert response.status_code == 422
    assert response.json()["error"] == "resolution_required"
    assert _actions(client, ticket.id, tech) == []  # nothing recorded on failure


def test_resolution_is_rejected_outside_resolve(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user, assigned_to=tech)

    response = _set_status(client, ticket.id, tech, "IN_PROGRESS", resolution=RESOLUTION)

    assert response.status_code == 422
    assert response.json()["error"] == "unexpected_resolution"


def test_regular_user_cannot_resolve(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=TicketStatus.IN_PROGRESS
    )

    response = _set_status(client, ticket.id, user, "RESOLVED", resolution=RESOLUTION)

    assert response.status_code == 403
    assert response.json()["error"] == "status_change_forbidden"


def test_invalid_transition_returns_409(
    client: TestClient, db_session: Session, user: User, tech: User, admin: User
) -> None:
    ticket = make_ticket(
        db_session,
        created_by=user,
        assigned_to=tech,
        status=TicketStatus.CLOSED,
        resolution=RESOLUTION,
    )

    response = _set_status(client, ticket.id, admin, "IN_PROGRESS")

    assert response.status_code == 409
    assert response.json() == {
        "error": "invalid_status_transition",
        "message": "Cannot move ticket from CLOSED to IN_PROGRESS",
    }


def test_work_cannot_start_without_technician(
    client: TestClient, db_session: Session, user: User, admin: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = _set_status(client, ticket.id, admin, "IN_PROGRESS")

    assert response.status_code == 422
    assert response.json()["error"] == "ticket_not_assigned"


def test_author_reopens_resolved_ticket(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session,
        created_by=user,
        assigned_to=tech,
        status=TicketStatus.RESOLVED,
        resolution=RESOLUTION,
    )

    response = _set_status(client, ticket.id, user, "IN_PROGRESS")

    assert response.status_code == 200
    assert response.json()["resolved_at"] is None
    assert response.json()["assigned_to"]["id"] == tech.id
    assert _actions(client, ticket.id, user) == ["REOPENED"]


def test_author_cancels_open_ticket(client: TestClient, db_session: Session, user: User) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = _set_status(client, ticket.id, user, "CANCELLED")

    assert response.status_code == 200
    assert response.json()["closed_at"] is not None
    edit = client.patch(
        f"{TICKETS_URL}/{ticket.id}", headers=auth_headers(user), json={"title": "Too late now"}
    )
    assert edit.status_code == 409


def test_status_change_follows_visibility(
    client: TestClient, db_session: Session, user: User
) -> None:
    ticket = make_ticket(db_session, created_by=make_user(db_session))

    response = _set_status(client, ticket.id, user, "CANCELLED")

    assert response.status_code == 404


def test_unknown_status_is_a_validation_error(
    client: TestClient, db_session: Session, user: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = _set_status(client, ticket.id, user, "DONE")

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
