from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Category, Ticket, TicketStatus, User, UserRole
from tests.factories import auth_headers, make_category, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


@pytest.fixture
def category(db_session: Session) -> Category:
    return make_category(db_session, name="Workstations")


@pytest.fixture
def user(db_session: Session) -> User:
    return make_user(db_session, name="Ana User")


@pytest.fixture
def other_user(db_session: Session) -> User:
    return make_user(db_session, name="Bruno User")


@pytest.fixture
def tech(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.TECHNICIAN, name="Carla Tech")


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.ADMIN)


def _payload(category: Category, **overrides: object) -> dict:
    return {
        "title": "Laptop does not turn on",
        "description": "Since this morning the laptop does not power on.",
        "category_id": category.id,
        **overrides,
    }


def _ids(response) -> set[int]:
    return {ticket["id"] for ticket in response.json()["items"]}


# --- create -----------------------------------------------------------------


def test_user_creates_ticket(client: TestClient, user: User, category: Category) -> None:
    response = client.post(TICKETS_URL, headers=auth_headers(user), json=_payload(category))

    body = response.json()
    assert response.status_code == 201
    assert body["status"] == "OPEN"
    assert body["priority"] == "MEDIUM"
    assert body["created_by"] == {"id": user.id, "name": "Ana User"}
    assert body["assigned_to"] is None
    assert body["category"] == {"id": category.id, "name": "Workstations"}
    assert body["resolution"] is None


def test_new_ticket_gets_sla_due_date_from_priority(
    client: TestClient, db_session: Session, user: User, category: Category
) -> None:
    response = client.post(
        TICKETS_URL, headers=auth_headers(user), json=_payload(category, priority="CRITICAL")
    )

    ticket = db_session.get(Ticket, response.json()["id"])
    assert ticket.sla_due_at - ticket.created_at == timedelta(hours=4)


def test_user_can_choose_priority(client: TestClient, user: User, category: Category) -> None:
    response = client.post(
        TICKETS_URL, headers=auth_headers(user), json=_payload(category, priority="HIGH")
    )

    assert response.json()["priority"] == "HIGH"


@pytest.mark.parametrize(
    "field", [{"status": "RESOLVED"}, {"assigned_to_id": 1}, {"resolution": "Done"}]
)
def test_workflow_fields_cannot_be_set_on_creation(
    client: TestClient, user: User, category: Category, field: dict
) -> None:
    response = client.post(
        TICKETS_URL, headers=auth_headers(user), json=_payload(category, **field)
    )

    assert response.status_code == 422


def test_ticket_requires_active_category(
    client: TestClient, db_session: Session, user: User
) -> None:
    inactive = make_category(db_session, is_active=False)

    response = client.post(TICKETS_URL, headers=auth_headers(user), json=_payload(inactive))

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_category"


def test_ticket_with_unknown_category_is_rejected(
    client: TestClient, user: User, category: Category
) -> None:
    response = client.post(
        TICKETS_URL, headers=auth_headers(user), json=_payload(category, category_id=999999)
    )

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_category"


def test_title_and_description_are_validated(
    client: TestClient, user: User, category: Category
) -> None:
    response = client.post(
        TICKETS_URL,
        headers=auth_headers(user),
        json=_payload(category, title="  Hi ", description="short"),
    )

    fields = {detail["field"] for detail in response.json()["details"]}
    assert response.status_code == 422
    assert fields == {"title", "description"}


def test_creating_ticket_requires_authentication(client: TestClient, category: Category) -> None:
    assert client.post(TICKETS_URL, json=_payload(category)).status_code == 401


# --- visibility -------------------------------------------------------------


def test_user_cannot_view_ticket_of_another_user(
    client: TestClient, db_session: Session, user: User, other_user: User
) -> None:
    ticket = make_ticket(db_session, created_by=other_user)

    response = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_headers(user))

    # 404, not 403: the existence of other people's tickets is not revealed.
    assert response.status_code == 404
    assert response.json()["error"] == "ticket_not_found"


def test_user_cannot_view_ticket_of_another_user_assigned_to_technician(
    client: TestClient, db_session: Session, user: User, other_user: User, tech: User
) -> None:
    ticket = make_ticket(
        db_session, created_by=other_user, assigned_to=tech, status=TicketStatus.IN_PROGRESS
    )

    response = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_headers(user))

    assert response.status_code == 404


def test_user_views_own_ticket(client: TestClient, db_session: Session, user: User) -> None:
    ticket = make_ticket(db_session, created_by=user)

    response = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["description"] == ticket.description


def test_user_lists_only_own_tickets(
    client: TestClient, db_session: Session, user: User, other_user: User
) -> None:
    mine = make_ticket(db_session, created_by=user)
    make_ticket(db_session, created_by=other_user)

    response = client.get(TICKETS_URL, headers=auth_headers(user))

    assert _ids(response) == {mine.id}


def test_technician_sees_available_assigned_and_own_tickets(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    other_tech = make_user(db_session, role=UserRole.TECHNICIAN)
    available = make_ticket(db_session, created_by=user)
    assigned_to_me = make_ticket(
        db_session, created_by=user, assigned_to=tech, status=TicketStatus.IN_PROGRESS
    )
    opened_by_me = make_ticket(db_session, created_by=tech, assigned_to=other_tech)
    make_ticket(db_session, created_by=user, assigned_to=other_tech)  # another tech's queue
    make_ticket(db_session, created_by=user, status=TicketStatus.CANCELLED)  # not available

    response = client.get(TICKETS_URL, headers=auth_headers(tech))

    assert _ids(response) == {available.id, assigned_to_me.id, opened_by_me.id}


def test_technician_cannot_view_ticket_assigned_to_another_technician(
    client: TestClient, db_session: Session, user: User, tech: User
) -> None:
    other_tech = make_user(db_session, role=UserRole.TECHNICIAN)
    ticket = make_ticket(db_session, created_by=user, assigned_to=other_tech)

    response = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_headers(tech))

    assert response.status_code == 404


def test_admin_sees_all_tickets(
    client: TestClient,
    db_session: Session,
    user: User,
    other_user: User,
    tech: User,
    admin: User,
) -> None:
    tickets = [
        make_ticket(db_session, created_by=user),
        make_ticket(db_session, created_by=other_user, assigned_to=tech),
        make_ticket(db_session, created_by=tech, status=TicketStatus.CANCELLED),
    ]

    response = client.get(TICKETS_URL, headers=auth_headers(admin))

    assert _ids(response) == {ticket.id for ticket in tickets}
    for ticket in tickets:
        detail = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_headers(admin))
        assert detail.status_code == 200


def test_list_is_paginated_newest_first(
    client: TestClient, db_session: Session, user: User
) -> None:
    created = [make_ticket(db_session, created_by=user) for _ in range(3)]

    response = client.get(TICKETS_URL, headers=auth_headers(user), params={"page_size": 2})

    body = response.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    # Same created_at inside one test transaction: the id breaks the tie.
    assert [t["id"] for t in body["items"]] == [created[2].id, created[1].id]
    assert "description" not in body["items"][0]


def test_unknown_ticket_returns_404(client: TestClient, admin: User) -> None:
    response = client.get(f"{TICKETS_URL}/999999", headers=auth_headers(admin))

    assert response.status_code == 404
