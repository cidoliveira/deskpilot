import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, UserRole
from tests.factories import auth_headers, make_user

USERS_URL = "/api/v1/users"


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.ADMIN)


@pytest.mark.parametrize("role", [UserRole.USER, UserRole.TECHNICIAN])
def test_only_admin_can_manage_users(
    client: TestClient, db_session: Session, role: UserRole
) -> None:
    headers = auth_headers(make_user(db_session, role=role))

    responses = [
        client.get(USERS_URL, headers=headers),
        client.post(USERS_URL, headers=headers, json={}),
        client.get(f"{USERS_URL}/1", headers=headers),
        client.patch(f"{USERS_URL}/1", headers=headers, json={}),
    ]

    assert {r.status_code for r in responses} == {403}
    assert responses[0].json()["error"] == "permission_denied"


def test_user_management_requires_authentication(client: TestClient) -> None:
    assert client.get(USERS_URL).status_code == 401


def test_admin_lists_users_with_pagination(
    client: TestClient, db_session: Session, admin: User
) -> None:
    for _ in range(3):
        make_user(db_session)

    response = client.get(USERS_URL, headers=auth_headers(admin), params={"page_size": 2})

    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 4
    assert len(body["items"]) == 2
    assert body["pages"] == 2


def test_admin_filters_technicians(client: TestClient, db_session: Session, admin: User) -> None:
    tech = make_user(db_session, role=UserRole.TECHNICIAN)
    make_user(db_session, role=UserRole.USER)

    response = client.get(USERS_URL, headers=auth_headers(admin), params={"role": "TECHNICIAN"})

    assert [u["id"] for u in response.json()["items"]] == [tech.id]


def test_page_size_is_limited(client: TestClient, admin: User) -> None:
    response = client.get(USERS_URL, headers=auth_headers(admin), params={"page_size": 1000})

    assert response.status_code == 422


def test_admin_creates_technician(client: TestClient, admin: User) -> None:
    response = client.post(
        USERS_URL,
        headers=auth_headers(admin),
        json={
            "name": "Carlos Tech",
            "email": "carlos@example.com",
            "password": "Str0ng-password",
            "role": "TECHNICIAN",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "TECHNICIAN"


def test_admin_gets_user_by_id(client: TestClient, db_session: Session, admin: User) -> None:
    user = make_user(db_session)

    response = client.get(f"{USERS_URL}/{user.id}", headers=auth_headers(admin))

    assert response.status_code == 200
    assert response.json()["email"] == user.email


def test_get_unknown_user_returns_404(client: TestClient, admin: User) -> None:
    response = client.get(f"{USERS_URL}/999999", headers=auth_headers(admin))

    assert response.status_code == 404
    assert response.json()["error"] == "user_not_found"


def test_admin_promotes_and_deactivates_user(
    client: TestClient, db_session: Session, admin: User
) -> None:
    user = make_user(db_session)

    response = client.patch(
        f"{USERS_URL}/{user.id}",
        headers=auth_headers(admin),
        json={"role": "TECHNICIAN", "is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "TECHNICIAN"
    assert response.json()["is_active"] is False


def test_admin_cannot_demote_self(client: TestClient, admin: User) -> None:
    response = client.patch(
        f"{USERS_URL}/{admin.id}", headers=auth_headers(admin), json={"role": "USER"}
    )

    assert response.status_code == 422
    assert response.json()["error"] == "cannot_change_own_role"


def test_update_cannot_change_email_or_password(
    client: TestClient, db_session: Session, admin: User
) -> None:
    user = make_user(db_session)

    response = client.patch(
        f"{USERS_URL}/{user.id}",
        headers=auth_headers(admin),
        json={"email": "new@example.com", "password": "Str0ng-password"},
    )

    assert response.status_code == 422
