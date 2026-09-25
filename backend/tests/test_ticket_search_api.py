from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, UserRole
from tests.factories import auth_headers, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.ADMIN)


def _ids(client: TestClient, user: User, **params) -> set[int]:
    response = client.get(TICKETS_URL, headers=auth_headers(user), params=params)
    assert response.status_code == 200, response.json()
    return {ticket["id"] for ticket in response.json()["items"]}


def test_search_matches_title_or_description_ignoring_case(
    client: TestClient, db_session: Session, admin: User
) -> None:
    in_title = make_ticket(db_session, created_by=admin, title="VPN keeps disconnecting")
    in_description = make_ticket(
        db_session, created_by=admin, description="The corporate vpn client shows error 809."
    )
    make_ticket(db_session, created_by=admin, title="Printer jam on 3rd floor")

    assert _ids(client, admin, q="vpn") == {in_title.id, in_description.id}


def test_search_treats_wildcards_literally(
    client: TestClient, db_session: Session, admin: User
) -> None:
    percent = make_ticket(db_session, created_by=admin, title="Disk at 100% usage")
    make_ticket(db_session, created_by=admin, title="Disk at 1000 IOPS")

    assert _ids(client, admin, q="100%") == {percent.id}
    assert _ids(client, admin, q="_") == set()


def test_filter_by_creation_date_range_is_inclusive(
    client: TestClient, db_session: Session, admin: User
) -> None:
    march_1 = make_ticket(
        db_session, created_by=admin, created_at=datetime(2026, 3, 1, 8, tzinfo=UTC)
    )
    march_2_late = make_ticket(
        db_session, created_by=admin, created_at=datetime(2026, 3, 2, 23, 59, tzinfo=UTC)
    )
    make_ticket(db_session, created_by=admin, created_at=datetime(2026, 3, 3, 0, 0, tzinfo=UTC))

    assert _ids(client, admin, created_from="2026-03-01", created_to="2026-03-02") == {
        march_1.id,
        march_2_late.id,
    }
    assert _ids(client, admin, created_from="2026-03-02", created_to="2026-03-02") == {
        march_2_late.id
    }


def test_inverted_date_range_is_a_validation_error(client: TestClient, admin: User) -> None:
    response = client.get(
        TICKETS_URL,
        headers=auth_headers(admin),
        params={"created_from": "2026-03-05", "created_to": "2026-03-01"},
    )

    assert response.status_code == 422
    assert response.json()["details"][0]["field"] == "created_to"


@pytest.mark.parametrize("params", [{"q": "x" * 101}, {"created_from": "yesterday"}])
def test_invalid_search_params_are_rejected(client: TestClient, admin: User, params: dict) -> None:
    assert client.get(TICKETS_URL, headers=auth_headers(admin), params=params).status_code == 422
