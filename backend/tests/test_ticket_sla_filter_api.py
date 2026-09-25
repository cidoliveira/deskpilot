from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import SlaStatus, TicketPriority, TicketStatus, User, UserRole
from tests.factories import auth_headers, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.ADMIN)


@pytest.fixture
def tickets_in_every_sla_state(db_session: Session, admin: User) -> dict[str, int]:
    """HIGH priority = 8h window. Returns ticket ids by expected SLA status."""
    now = datetime.now(UTC)
    high = TicketPriority.HIGH

    def resolved(created_hours_ago: float, resolved_after_hours: float) -> int:
        created = now - timedelta(hours=created_hours_ago)
        return make_ticket(
            db_session,
            created_by=admin,
            assigned_to=admin,
            priority=high,
            status=TicketStatus.RESOLVED,
            resolution="Done.",
            created_at=created,
            resolved_at=created + timedelta(hours=resolved_after_hours),
        ).id

    def open_since(hours_ago: float) -> int:
        created = now - timedelta(hours=hours_ago)
        return make_ticket(db_session, created_by=admin, priority=high, created_at=created).id

    return {
        "ON_TRACK": open_since(1),
        "AT_RISK": open_since(7),  # 87% of the window
        "BREACHED": open_since(9),
        "BREACHED_RESOLVED_LATE": resolved(24, 10),
        "MET": resolved(24, 2),
        "CANCELLED": make_ticket(
            db_session,
            created_by=admin,
            status=TicketStatus.CANCELLED,
            created_at=now - timedelta(days=5),
        ).id,
    }


def _listed(client: TestClient, admin: User, **params) -> dict[int, str | None]:
    response = client.get(TICKETS_URL, headers=auth_headers(admin), params=params)
    assert response.status_code == 200
    return {t["id"]: t["sla_status"] for t in response.json()["items"]}


def test_filter_by_sla_status(
    client: TestClient, admin: User, tickets_in_every_sla_state: dict[str, int]
) -> None:
    ids = tickets_in_every_sla_state

    assert set(_listed(client, admin, sla_status="ON_TRACK")) == {ids["ON_TRACK"]}
    assert set(_listed(client, admin, sla_status="AT_RISK")) == {ids["AT_RISK"]}
    assert set(_listed(client, admin, sla_status="MET")) == {ids["MET"]}
    assert set(_listed(client, admin, sla_status="BREACHED")) == {
        ids["BREACHED"],
        ids["BREACHED_RESOLVED_LATE"],
    }


@pytest.mark.parametrize("status", list(SlaStatus))
def test_sql_filter_agrees_with_computed_status(
    client: TestClient,
    admin: User,
    tickets_in_every_sla_state: dict[str, int],
    status: SlaStatus,
) -> None:
    """The SLA rule exists twice (Python for responses, SQL for filters): they must agree."""
    listed = _listed(client, admin, sla_status=status.value)

    assert listed
    assert set(listed.values()) == {status.value}


def test_cancelled_tickets_match_no_sla_filter(
    client: TestClient, admin: User, tickets_in_every_sla_state: dict[str, int]
) -> None:
    cancelled = tickets_in_every_sla_state["CANCELLED"]

    for status in SlaStatus:
        assert cancelled not in _listed(client, admin, sla_status=status.value)
