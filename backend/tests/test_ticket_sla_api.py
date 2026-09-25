from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TicketPriority, TicketStatus, UserRole
from tests.factories import auth_headers, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


def test_ticket_responses_include_sla(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)
    two_days_ago = datetime.now(UTC) - timedelta(days=2)
    overdue = make_ticket(
        db_session, created_by=admin, priority=TicketPriority.CRITICAL, created_at=two_days_ago
    )
    fresh = make_ticket(db_session, created_by=admin, priority=TicketPriority.LOW)

    detail = client.get(f"{TICKETS_URL}/{overdue.id}", headers=auth_headers(admin)).json()
    listed = client.get(TICKETS_URL, headers=auth_headers(admin)).json()["items"]

    assert detail["sla_status"] == "BREACHED"
    assert detail["sla_due_at"] is not None
    assert {t["id"]: t["sla_status"] for t in listed} == {
        overdue.id: "BREACHED",
        fresh.id: "ON_TRACK",
    }


def test_ticket_resolved_on_time_is_met(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)
    created = datetime.now(UTC) - timedelta(days=3)
    ticket = make_ticket(
        db_session,
        created_by=admin,
        assigned_to=admin,
        status=TicketStatus.RESOLVED,
        resolution="Fixed quickly.",
        priority=TicketPriority.HIGH,
        created_at=created,
        resolved_at=created + timedelta(hours=1),
    )

    detail = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_headers(admin)).json()

    assert detail["sla_status"] == "MET"


def test_cancelled_ticket_has_no_sla_status(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    ticket = make_ticket(db_session, created_by=user, status=TicketStatus.CANCELLED)

    detail = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_headers(user)).json()

    assert detail["sla_status"] is None
