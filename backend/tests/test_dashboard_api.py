from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TicketPriority, TicketStatus, User, UserRole
from tests.factories import auth_headers, make_category, make_ticket, make_user

METRICS_URL = "/api/v1/dashboard/metrics"


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.ADMIN)


@pytest.fixture
def scenario(db_session: Session, admin: User) -> dict:
    """A small, fully known data set (all created "now" unless stated)."""
    now = datetime.now(UTC)
    user = make_user(db_session)
    carla = make_user(db_session, role=UserRole.TECHNICIAN, name="Carla Tech")
    diego = make_user(db_session, role=UserRole.TECHNICIAN, name="Diego Tech")
    network = make_category(db_session, name="Net X")
    printers = make_category(db_session, name="Print X")

    def resolved(tech: User, hours_to_resolve: float, priority=TicketPriority.HIGH) -> None:
        created = now - timedelta(days=1)
        make_ticket(
            db_session,
            created_by=user,
            assigned_to=tech,
            category=network,
            priority=priority,
            status=TicketStatus.CLOSED,
            resolution="Done.",
            created_at=created,
            resolved_at=created + timedelta(hours=hours_to_resolve),
        )

    make_ticket(db_session, created_by=user, category=network)  # OPEN, on track
    make_ticket(
        db_session,
        created_by=user,
        category=printers,
        assigned_to=carla,
        status=TicketStatus.IN_PROGRESS,
        priority=TicketPriority.CRITICAL,
        created_at=now - timedelta(hours=5),  # 4h SLA: breached, still open
    )
    make_ticket(
        db_session,
        created_by=user,
        category=printers,
        assigned_to=carla,
        status=TicketStatus.WAITING_USER,
        priority=TicketPriority.HIGH,
        created_at=now - timedelta(hours=7),  # 8h SLA: at risk
    )
    resolved(carla, hours_to_resolve=2)  # HIGH, met
    resolved(diego, hours_to_resolve=4)  # HIGH, met
    resolved(diego, hours_to_resolve=12)  # HIGH, breached
    make_ticket(db_session, created_by=user, status=TicketStatus.CANCELLED)
    return {"carla": carla, "diego": diego, "network": network, "printers": printers}


def _metrics(client: TestClient, admin: User, **params) -> dict:
    response = client.get(METRICS_URL, headers=auth_headers(admin), params=params)
    assert response.status_code == 200, response.json()
    return response.json()


def test_volume_by_status_and_priority(client: TestClient, admin: User, scenario: dict) -> None:
    metrics = _metrics(client, admin)

    assert metrics["total"] == 7
    assert metrics["by_status"] == {
        "OPEN": 1,
        "IN_PROGRESS": 1,
        "WAITING_USER": 1,
        "RESOLVED": 0,
        "CLOSED": 3,
        "CANCELLED": 1,
    }
    assert metrics["by_priority"] == {"LOW": 0, "MEDIUM": 2, "HIGH": 4, "CRITICAL": 1}


def test_volume_by_category(client: TestClient, admin: User, scenario: dict) -> None:
    by_category = _metrics(client, admin)["by_category"]
    counts = {item["name"]: item["count"] for item in by_category}

    assert counts["Net X"] == 4
    assert counts["Print X"] == 2
    assert by_category[0]["name"] == "Net X"  # busiest first


def test_sla_metrics(client: TestClient, admin: User, scenario: dict) -> None:
    assert _metrics(client, admin)["sla"] == {
        "at_risk": 1,
        "breached_open": 1,
        "breached_resolved": 1,
        "met": 2,
        "compliance_rate": 0.6667,
    }


def test_average_resolution_time(client: TestClient, admin: User, scenario: dict) -> None:
    assert _metrics(client, admin)["avg_resolution_hours"] == 6.0  # (2 + 4 + 12) / 3


def test_workload_by_technician(client: TestClient, admin: User, scenario: dict) -> None:
    workload = {
        item["technician"]["name"]: (item["open"], item["resolved"])
        for item in _metrics(client, admin)["by_technician"]
    }

    assert workload == {"Carla Tech": (2, 1), "Diego Tech": (0, 2)}


def test_date_range_limits_the_metrics(client: TestClient, admin: User, scenario: dict) -> None:
    today = datetime.now(UTC).date()

    metrics = _metrics(client, admin, created_from=today.isoformat())

    assert metrics["total"] == 4  # the three resolved tickets were created yesterday
    assert metrics["avg_resolution_hours"] is None
    assert metrics["sla"]["compliance_rate"] is None


def test_empty_database_returns_zeros(client: TestClient, admin: User) -> None:
    metrics = _metrics(client, admin)

    assert metrics["total"] == 0
    assert set(metrics["by_status"].values()) == {0}
    assert metrics["by_category"] == []
    assert metrics["by_technician"] == []


def test_inverted_date_range_is_rejected(client: TestClient, admin: User) -> None:
    response = client.get(
        METRICS_URL,
        headers=auth_headers(admin),
        params={"created_from": "2026-03-05", "created_to": "2026-03-01"},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_date_range"


@pytest.mark.parametrize("role", [UserRole.USER, UserRole.TECHNICIAN])
def test_only_admin_sees_metrics(client: TestClient, db_session: Session, role: UserRole) -> None:
    response = client.get(METRICS_URL, headers=auth_headers(make_user(db_session, role=role)))

    assert response.status_code == 403
