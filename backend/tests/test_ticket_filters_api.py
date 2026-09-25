import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TicketPriority, TicketStatus, User, UserRole
from tests.factories import auth_headers, make_category, make_ticket, make_user

TICKETS_URL = "/api/v1/tickets"


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.ADMIN)


@pytest.fixture
def tech(db_session: Session) -> User:
    return make_user(db_session, role=UserRole.TECHNICIAN)


def _ids(client: TestClient, user: User, **params) -> set[int]:
    response = client.get(TICKETS_URL, headers=auth_headers(user), params=params)
    assert response.status_code == 200, response.json()
    return {ticket["id"] for ticket in response.json()["items"]}


def test_filter_by_one_or_more_statuses(
    client: TestClient, db_session: Session, admin: User, tech: User
) -> None:
    open_ = make_ticket(db_session, created_by=admin)
    in_progress = make_ticket(
        db_session, created_by=admin, assigned_to=tech, status=TicketStatus.IN_PROGRESS
    )
    make_ticket(db_session, created_by=admin, status=TicketStatus.CANCELLED)

    assert _ids(client, admin, status="OPEN") == {open_.id}
    assert _ids(client, admin, status=["OPEN", "IN_PROGRESS"]) == {open_.id, in_progress.id}


def test_filter_by_priority(client: TestClient, db_session: Session, admin: User) -> None:
    critical = make_ticket(db_session, created_by=admin, priority=TicketPriority.CRITICAL)
    make_ticket(db_session, created_by=admin, priority=TicketPriority.LOW)

    assert _ids(client, admin, priority="CRITICAL") == {critical.id}


def test_filter_by_category(client: TestClient, db_session: Session, admin: User) -> None:
    printers = make_category(db_session, name="Printers X")
    printer_ticket = make_ticket(db_session, created_by=admin, category=printers)
    make_ticket(db_session, created_by=admin)

    assert _ids(client, admin, category_id=printers.id) == {printer_ticket.id}


def test_filter_by_assignee(
    client: TestClient, db_session: Session, admin: User, tech: User
) -> None:
    mine = make_ticket(db_session, created_by=admin, assigned_to=tech)
    unassigned = make_ticket(db_session, created_by=admin)
    make_ticket(db_session, created_by=admin, assigned_to=admin)

    assert _ids(client, admin, assignee=str(tech.id)) == {mine.id}
    assert _ids(client, admin, assignee="none") == {unassigned.id}
    assert _ids(client, tech, assignee="me") == {mine.id}


def test_filter_by_author(client: TestClient, db_session: Session, admin: User) -> None:
    ana = make_user(db_session)
    anas_ticket = make_ticket(db_session, created_by=ana)
    make_ticket(db_session, created_by=make_user(db_session))

    assert _ids(client, admin, created_by_id=ana.id) == {anas_ticket.id}


def test_filters_never_widen_visibility(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    other = make_user(db_session)
    make_ticket(db_session, created_by=other)

    assert _ids(client, user, created_by_id=other.id) == set()


def test_filters_are_combined_with_and(
    client: TestClient, db_session: Session, admin: User
) -> None:
    match = make_ticket(
        db_session, created_by=admin, status=TicketStatus.OPEN, priority=TicketPriority.HIGH
    )
    make_ticket(db_session, created_by=admin, status=TicketStatus.OPEN)
    make_ticket(
        db_session, created_by=admin, status=TicketStatus.CANCELLED, priority=TicketPriority.HIGH
    )

    assert _ids(client, admin, status="OPEN", priority="HIGH") == {match.id}


def test_filtered_list_is_paginated(client: TestClient, db_session: Session, admin: User) -> None:
    for _ in range(3):
        make_ticket(db_session, created_by=admin, priority=TicketPriority.LOW)
    make_ticket(db_session, created_by=admin)

    body = client.get(
        TICKETS_URL, headers=auth_headers(admin), params={"priority": "LOW", "page_size": 2}
    ).json()

    assert body["total"] == 3
    assert body["pages"] == 2


@pytest.mark.parametrize(
    "params", [{"status": "DONE"}, {"priority": "URGENT"}, {"assignee": "someone"}]
)
def test_invalid_filter_values_are_rejected(client: TestClient, admin: User, params: dict) -> None:
    response = client.get(TICKETS_URL, headers=auth_headers(admin), params=params)

    assert response.status_code == 422
