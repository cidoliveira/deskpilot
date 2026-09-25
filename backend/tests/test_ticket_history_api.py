import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Category, User
from tests.factories import auth_headers, make_category, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


@pytest.fixture
def user(db_session: Session) -> User:
    return make_user(db_session, name="Ana User")


@pytest.fixture
def category(db_session: Session) -> Category:
    return make_category(db_session, name="Workstations")


def _history(client: TestClient, ticket_id: int, user: User) -> list[dict]:
    response = client.get(f"{TICKETS_URL}/{ticket_id}/history", headers=auth_headers(user))
    assert response.status_code == 200
    return response.json()


def test_ticket_creation_is_recorded(client: TestClient, user: User, category: Category) -> None:
    created = client.post(
        TICKETS_URL,
        headers=auth_headers(user),
        json={
            "title": "Monitor flickering",
            "description": "The external monitor flickers every few seconds.",
            "category_id": category.id,
        },
    ).json()

    history = _history(client, created["id"], user)

    assert len(history) == 1
    assert history[0]["action"] == "CREATED"
    assert history[0]["new_value"] == "OPEN"
    assert history[0]["changed_by"] == {"id": user.id, "name": "Ana User"}


def test_category_change_is_recorded_with_labels(
    client: TestClient, db_session: Session, user: User, category: Category
) -> None:
    ticket = make_ticket(db_session, created_by=user, category=category)
    peripherals = make_category(db_session, name="Peripherals")

    client.patch(
        f"{TICKETS_URL}/{ticket.id}",
        headers=auth_headers(user),
        json={"category_id": peripherals.id},
    )

    [event] = _history(client, ticket.id, user)
    assert event["action"] == "CATEGORY_CHANGED"
    assert (event["old_value"], event["new_value"]) == (str(category.id), str(peripherals.id))
    assert (event["old_label"], event["new_label"]) == ("Workstations", "Peripherals")


def test_editing_title_or_same_category_does_not_create_events(
    client: TestClient, db_session: Session, user: User, category: Category
) -> None:
    ticket = make_ticket(db_session, created_by=user, category=category)

    client.patch(
        f"{TICKETS_URL}/{ticket.id}",
        headers=auth_headers(user),
        json={"title": "A better title", "category_id": category.id},
    )

    assert _history(client, ticket.id, user) == []


def test_history_follows_ticket_visibility(
    client: TestClient, db_session: Session, user: User
) -> None:
    ticket = make_ticket(db_session, created_by=make_user(db_session))

    response = client.get(f"{TICKETS_URL}/{ticket.id}/history", headers=auth_headers(user))

    assert response.status_code == 404
