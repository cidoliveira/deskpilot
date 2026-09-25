import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TicketStatus, User, UserRole
from tests.factories import auth_headers, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


@pytest.fixture
def user(db_session: Session) -> User:
    return make_user(db_session, name="Ana User")


@pytest.fixture
def tech(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.TECHNICIAN, name="Carla Tech")


def _comment(client: TestClient, ticket_id: int, author: User, message: str):
    return client.post(
        f"{TICKETS_URL}/{ticket_id}/comments",
        headers=auth_headers(author),
        json={"message": message},
    )


def _comments(client: TestClient, ticket_id: int, user: User):
    return client.get(f"{TICKETS_URL}/{ticket_id}/comments", headers=auth_headers(user))


def test_author_comments_on_own_ticket(client: TestClient, db_session: Session, user: User) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = _comment(client, ticket.id, user, "  It also happens on the second monitor.  ")

    body = response.json()
    assert response.status_code == 201
    assert body["message"] == "It also happens on the second monitor."
    assert body["author"] == {"id": user.id, "name": "Ana User"}
    assert body["ticket_id"] == ticket.id


def test_conversation_is_listed_oldest_first(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=TicketStatus.IN_PROGRESS
    )

    _comment(client, ticket.id, tech, "Can you restart the laptop?")
    _comment(client, ticket.id, user, "Done, still broken.")
    response = _comments(client, ticket.id, user)

    assert response.status_code == 200
    assert [(c["author"]["name"], c["message"]) for c in response.json()] == [
        ("Carla Tech", "Can you restart the laptop?"),
        ("Ana User", "Done, still broken."),
    ]


@pytest.mark.parametrize("status", [TicketStatus.CLOSED, TicketStatus.CANCELLED])
def test_closed_ticket_does_not_accept_comments(
    client: TestClient, db_session: Session, user: User, tech: User, status: TicketStatus
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=status, resolution="Fixed it."
    )

    response = _comment(client, ticket.id, user, "Hello?")

    assert response.status_code == 409
    assert response.json()["error"] == "ticket_closed"
    assert _comments(client, ticket.id, user).json() == []


def test_resolved_ticket_still_accepts_comments(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session,
        created_by=user,
        assigned_to=tech,
        status=TicketStatus.RESOLVED,
        resolution="Fixed it.",
    )

    assert _comment(client, ticket.id, user, "Thanks, it works now!").status_code == 201


def test_comments_follow_ticket_visibility(
    client: TestClient, db_session: Session, user: User
) -> None:
    ticket = make_ticket(db_session, created_by=make_user(db_session))

    assert _comment(client, ticket.id, user, "Let me in").status_code == 404
    assert _comments(client, ticket.id, user).status_code == 404


def test_technician_can_comment_on_available_ticket(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)

    assert _comment(client, ticket.id, tech, "Is this urgent?").status_code == 201


@pytest.mark.parametrize("message", ["", "   ", "x" * 5001])
def test_message_is_validated(
    client: TestClient, db_session: Session, user: User, message: str
) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = _comment(client, ticket.id, user, message)

    assert response.status_code == 422


def test_author_answer_resumes_ticket_waiting_for_user(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=TicketStatus.WAITING_USER
    )

    _comment(client, ticket.id, user, "Here is the screenshot you asked for.")

    detail = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_headers(user)).json()
    history = client.get(f"{TICKETS_URL}/{ticket.id}/history", headers=auth_headers(user)).json()
    assert detail["status"] == "IN_PROGRESS"
    assert [
        (e["action"], e["old_value"], e["new_value"], e["changed_by"]["id"]) for e in history
    ] == [("STATUS_CHANGED", "WAITING_USER", "IN_PROGRESS", user.id)]


def test_technician_comment_keeps_ticket_waiting(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=TicketStatus.WAITING_USER
    )

    _comment(client, ticket.id, tech, "Reminder: we still need the screenshot.")

    detail = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_headers(user)).json()
    assert detail["status"] == "WAITING_USER"


def test_author_comment_in_other_statuses_does_not_change_status(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=TicketStatus.IN_PROGRESS
    )

    _comment(client, ticket.id, user, "Any news?")

    history = client.get(f"{TICKETS_URL}/{ticket.id}/history", headers=auth_headers(user)).json()
    assert history == []


def test_commenting_requires_authentication(
    client: TestClient, db_session: Session, user: User
) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = client.post(f"{TICKETS_URL}/{ticket.id}/comments", json={"message": "Hi"})

    assert response.status_code == 401
