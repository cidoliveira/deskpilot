"""Unit tests for the edit policy: plain objects, no database."""

import pytest

from app.models import Ticket, TicketStatus, User, UserRole
from app.services.ticket_policy import can_edit

AUTHOR, TECH, OTHER_TECH, ADMIN, STRANGER = 1, 2, 3, 4, 5


def _user(user_id: int, role: UserRole) -> User:
    return User(id=user_id, role=role)


def _ticket(status: TicketStatus, assigned_to_id: int | None = None) -> Ticket:
    return Ticket(created_by_id=AUTHOR, assigned_to_id=assigned_to_id, status=status)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (TicketStatus.OPEN, True),
        (TicketStatus.IN_PROGRESS, False),
        (TicketStatus.WAITING_USER, False),
        (TicketStatus.RESOLVED, False),
    ],
)
def test_author_edits_only_while_open(status: TicketStatus, expected: bool) -> None:
    assert can_edit(_user(AUTHOR, UserRole.USER), _ticket(status, TECH)) is expected


def test_assigned_technician_can_edit() -> None:
    ticket = _ticket(TicketStatus.IN_PROGRESS, assigned_to_id=TECH)

    assert can_edit(_user(TECH, UserRole.TECHNICIAN), ticket)


def test_other_technician_cannot_edit() -> None:
    ticket = _ticket(TicketStatus.OPEN, assigned_to_id=TECH)

    assert not can_edit(_user(OTHER_TECH, UserRole.TECHNICIAN), ticket)


def test_technician_cannot_edit_unassigned_ticket_they_can_see() -> None:
    assert not can_edit(_user(OTHER_TECH, UserRole.TECHNICIAN), _ticket(TicketStatus.OPEN))


def test_admin_can_edit_any_ticket() -> None:
    ticket = _ticket(TicketStatus.WAITING_USER, assigned_to_id=TECH)

    assert can_edit(_user(ADMIN, UserRole.ADMIN), ticket)


def test_stranger_cannot_edit() -> None:
    assert not can_edit(_user(STRANGER, UserRole.USER), _ticket(TicketStatus.OPEN))
