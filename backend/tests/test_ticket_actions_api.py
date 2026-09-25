from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TicketStatus, User, UserRole
from tests.factories import auth_headers, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


def _actions(client: TestClient, ticket_id: int, user: User) -> dict:
    response = client.get(f"{TICKETS_URL}/{ticket_id}", headers=auth_headers(user))
    assert response.status_code == 200
    return response.json()["allowed_actions"]


def test_author_of_open_ticket(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    ticket = make_ticket(db_session, created_by=user)

    assert _actions(client, ticket.id, user) == {
        "can_edit": True,
        "can_claim": False,
        "can_assign": False,
        "can_change_priority": False,
        "can_comment": True,
        "allowed_transitions": ["CANCELLED"],
    }


def test_technician_on_available_ticket_can_only_claim(
    client: TestClient, db_session: Session
) -> None:
    tech = make_user(db_session, role=UserRole.TECHNICIAN)
    ticket = make_ticket(db_session, created_by=make_user(db_session))

    actions = _actions(client, ticket.id, tech)

    assert actions["can_claim"] is True
    assert actions["can_edit"] is False
    assert actions["allowed_transitions"] == []


def test_assigned_technician_working_on_ticket(client: TestClient, db_session: Session) -> None:
    tech = make_user(db_session, role=UserRole.TECHNICIAN)
    ticket = make_ticket(
        db_session,
        created_by=make_user(db_session),
        assigned_to=tech,
        status=TicketStatus.IN_PROGRESS,
    )

    actions = _actions(client, ticket.id, tech)

    assert actions["can_edit"] is True
    assert actions["can_claim"] is False
    assert actions["can_change_priority"] is True
    assert set(actions["allowed_transitions"]) == {"WAITING_USER", "RESOLVED"}


def test_author_of_resolved_ticket_can_close_or_reopen(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    ticket = make_ticket(
        db_session,
        created_by=user,
        assigned_to=make_user(db_session, role=UserRole.TECHNICIAN),
        status=TicketStatus.RESOLVED,
        resolution="Restarted the print spooler.",
    )

    assert set(_actions(client, ticket.id, user)["allowed_transitions"]) == {
        "CLOSED",
        "IN_PROGRESS",
    }


def test_nothing_is_allowed_on_closed_ticket_even_for_admin(
    client: TestClient, db_session: Session
) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)
    ticket = make_ticket(
        db_session,
        created_by=make_user(db_session),
        assigned_to=make_user(db_session, role=UserRole.TECHNICIAN),
        status=TicketStatus.CLOSED,
        resolution="Restarted the print spooler.",
    )

    assert _actions(client, ticket.id, admin) == {
        "can_edit": False,
        "can_claim": False,
        "can_assign": False,
        "can_change_priority": False,
        "can_comment": False,
        "allowed_transitions": [],
    }


def test_workflow_responses_include_updated_actions(
    client: TestClient, db_session: Session
) -> None:
    tech = make_user(db_session, role=UserRole.TECHNICIAN)
    ticket = make_ticket(db_session, created_by=make_user(db_session))

    response = client.put(
        f"{TICKETS_URL}/{ticket.id}/assignee",
        headers=auth_headers(tech),
        json={"assignee_id": tech.id},
    )

    actions = response.json()["allowed_actions"]
    assert actions["can_claim"] is False
    assert actions["allowed_transitions"] == ["IN_PROGRESS"]
