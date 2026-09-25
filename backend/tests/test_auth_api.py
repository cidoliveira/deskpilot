from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import UserRole
from tests.factories import DEFAULT_PASSWORD, auth_headers, make_user

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"


def _login(client: TestClient, email: str, password: str = DEFAULT_PASSWORD):
    return client.post(LOGIN_URL, data={"username": email, "password": password})


# --- register ---------------------------------------------------------------


def test_register_creates_user_without_exposing_password(client: TestClient) -> None:
    response = client.post(
        REGISTER_URL,
        json={"name": "Ana Souza", "email": "Ana@Example.com", "password": "Str0ng-password"},
    )

    body = response.json()
    assert response.status_code == 201
    assert body["email"] == "ana@example.com"
    assert body["role"] == "USER"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_cannot_choose_role(client: TestClient) -> None:
    # Privilege escalation attempt: extra fields are rejected, not silently ignored.
    response = client.post(
        REGISTER_URL,
        json={
            "name": "Eve",
            "email": "eve@example.com",
            "password": "Str0ng-password",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 422
    assert response.json()["details"][0]["field"] == "role"


def test_register_rejects_duplicate_email(client: TestClient, db_session: Session) -> None:
    make_user(db_session, email="ana@example.com")

    response = client.post(
        REGISTER_URL,
        json={"name": "Ana", "email": "ANA@example.com", "password": "Str0ng-password"},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "email_already_registered"


def test_register_rejects_short_password_and_invalid_email(client: TestClient) -> None:
    response = client.post(
        REGISTER_URL, json={"name": "Ana", "email": "not-an-email", "password": "123"}
    )

    fields = {detail["field"] for detail in response.json()["details"]}
    assert response.status_code == 422
    assert fields == {"email", "password"}


# --- login ------------------------------------------------------------------


def test_login_returns_bearer_token(client: TestClient, db_session: Session) -> None:
    make_user(db_session, email="ana@example.com")

    response = _login(client, "ANA@example.com")

    body = response.json()
    assert response.status_code == 200
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    me = client.get(ME_URL, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200


def test_login_with_wrong_password_fails(client: TestClient, db_session: Session) -> None:
    make_user(db_session, email="ana@example.com")

    response = _login(client, "ana@example.com", "wrong-password")

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_credentials"


def test_login_does_not_reveal_unknown_email(client: TestClient, db_session: Session) -> None:
    make_user(db_session, email="ana@example.com")

    wrong_password = _login(client, "ana@example.com", "wrong-password").json()
    unknown_email = _login(client, "nobody@example.com").json()

    assert unknown_email == wrong_password


def test_inactive_user_cannot_login(client: TestClient, db_session: Session) -> None:
    make_user(db_session, email="ana@example.com", is_active=False)

    response = _login(client, "ana@example.com")

    assert response.status_code == 403
    assert response.json()["error"] == "user_inactive"


# --- me / token validation --------------------------------------------------


def test_me_returns_current_user(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role=UserRole.TECHNICIAN)

    response = client.get(ME_URL, headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["id"] == user.id
    assert response.json()["role"] == "TECHNICIAN"


def test_me_requires_token(client: TestClient) -> None:
    response = client.get(ME_URL)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"] == "unauthorized"


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get(ME_URL, headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_token"


def test_me_rejects_expired_token(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    token = create_access_token(str(user.id), now=datetime.now(UTC) - timedelta(days=1))

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["error"] == "token_expired"


def test_token_of_deactivated_user_stops_working(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    headers = auth_headers(user)
    user.is_active = False
    db_session.flush()

    response = client.get(ME_URL, headers=headers)

    assert response.status_code == 401


def test_token_of_deleted_user_is_rejected(client: TestClient) -> None:
    token = create_access_token("999999")

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_role_change_takes_effect_without_new_token(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, role=UserRole.USER)
    headers = auth_headers(user)
    user.role = UserRole.TECHNICIAN
    db_session.flush()

    response = client.get(ME_URL, headers=headers)

    assert response.json()["role"] == "TECHNICIAN"
