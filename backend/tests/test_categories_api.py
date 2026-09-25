import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, UserRole
from tests.factories import auth_headers, make_category, make_user

CATEGORIES_URL = "/api/v1/categories"
DEFAULT_CATEGORIES = {"Hardware", "Software", "Network", "Access", "Email", "Printer", "Other"}


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.ADMIN)


@pytest.fixture
def user(db_session: Session) -> User:
    return make_user(db_session)


def _names(response) -> set[str]:
    return {category["name"] for category in response.json()}


def test_default_categories_are_seeded_by_migration(client: TestClient, user: User) -> None:
    response = client.get(CATEGORIES_URL, headers=auth_headers(user))

    assert response.status_code == 200
    assert _names(response) >= DEFAULT_CATEGORIES


def test_listing_categories_requires_authentication(client: TestClient) -> None:
    assert client.get(CATEGORIES_URL).status_code == 401


def test_inactive_categories_are_hidden(
    client: TestClient, db_session: Session, user: User
) -> None:
    make_category(db_session, name="Legacy ERP", is_active=False)

    response = client.get(CATEGORIES_URL, headers=auth_headers(user))

    assert "Legacy ERP" not in _names(response)


def test_only_admin_can_see_inactive_categories(
    client: TestClient, db_session: Session, user: User, admin: User
) -> None:
    make_category(db_session, name="Legacy ERP", is_active=False)
    params = {"include_inactive": "true"}

    as_user = client.get(CATEGORIES_URL, headers=auth_headers(user), params=params)
    as_admin = client.get(CATEGORIES_URL, headers=auth_headers(admin), params=params)

    assert "Legacy ERP" not in _names(as_user)
    assert "Legacy ERP" in _names(as_admin)


@pytest.mark.parametrize("role", [UserRole.USER, UserRole.TECHNICIAN])
def test_only_admin_can_manage_categories(
    client: TestClient, db_session: Session, role: UserRole
) -> None:
    headers = auth_headers(make_user(db_session, role=role))

    created = client.post(CATEGORIES_URL, headers=headers, json={"name": "Phones"})
    updated = client.patch(f"{CATEGORIES_URL}/1", headers=headers, json={"name": "Phones"})

    assert created.status_code == 403
    assert updated.status_code == 403


def test_admin_creates_category(client: TestClient, admin: User) -> None:
    response = client.post(
        CATEGORIES_URL,
        headers=auth_headers(admin),
        json={"name": "  Phones  ", "description": "Desk and mobile phones"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Phones"
    assert response.json()["is_active"] is True


def test_category_names_are_unique_ignoring_case(client: TestClient, admin: User) -> None:
    response = client.post(CATEGORIES_URL, headers=auth_headers(admin), json={"name": "network"})

    assert response.status_code == 409
    assert response.json()["error"] == "category_name_taken"


def test_admin_renames_and_deactivates_category(
    client: TestClient, db_session: Session, admin: User
) -> None:
    category = make_category(db_session, name="Phones")

    response = client.patch(
        f"{CATEGORIES_URL}/{category.id}",
        headers=auth_headers(admin),
        json={"name": "Telephony", "is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Telephony"
    assert response.json()["is_active"] is False


def test_rename_to_existing_name_is_rejected(
    client: TestClient, db_session: Session, admin: User
) -> None:
    category = make_category(db_session, name="Phones")

    response = client.patch(
        f"{CATEGORIES_URL}/{category.id}", headers=auth_headers(admin), json={"name": "EMAIL"}
    )

    assert response.status_code == 409


def test_update_unknown_category_returns_404(client: TestClient, admin: User) -> None:
    response = client.patch(
        f"{CATEGORIES_URL}/999999", headers=auth_headers(admin), json={"name": "Phones"}
    )

    assert response.status_code == 404
    assert response.json()["error"] == "category_not_found"


def test_category_name_cannot_be_null(client: TestClient, db_session: Session, admin: User) -> None:
    category = make_category(db_session, name="Phones")

    response = client.patch(
        f"{CATEGORIES_URL}/{category.id}", headers=auth_headers(admin), json={"name": None}
    )

    assert response.status_code == 422
