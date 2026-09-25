"""Unit tests for the SLA rules: plain values, `now` is always injected."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models import SlaStatus, TicketPriority, TicketStatus
from app.services import sla

CREATED = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)
DUE = CREATED + timedelta(hours=10)


def _status(now: datetime, *, resolved_at=None, status=TicketStatus.IN_PROGRESS):
    return sla.sla_status(
        status=status, created_at=CREATED, due=DUE, resolved_at=resolved_at, now=now
    )


@pytest.mark.parametrize(
    ("priority", "hours"),
    [
        (TicketPriority.CRITICAL, 4),
        (TicketPriority.HIGH, 8),
        (TicketPriority.MEDIUM, 24),
        (TicketPriority.LOW, 48),
    ],
)
def test_due_date_depends_on_priority(priority: TicketPriority, hours: int) -> None:
    assert sla.due_at(CREATED, priority) == CREATED + timedelta(hours=hours)


@pytest.mark.parametrize(
    ("elapsed_hours", "expected"),
    [
        (0, SlaStatus.ON_TRACK),
        (7.9, SlaStatus.ON_TRACK),
        (8, SlaStatus.AT_RISK),  # 80% of the 10h window
        (10, SlaStatus.AT_RISK),  # exactly at the due date is still on time
        (10.01, SlaStatus.BREACHED),
    ],
)
def test_open_ticket_status_over_time(elapsed_hours: float, expected: SlaStatus) -> None:
    assert _status(CREATED + timedelta(hours=elapsed_hours)) == expected


def test_resolved_on_time_is_met_forever() -> None:
    resolved = DUE - timedelta(minutes=1)

    assert _status(DUE + timedelta(days=30), resolved_at=resolved) == SlaStatus.MET


def test_resolved_late_is_breached() -> None:
    resolved = DUE + timedelta(minutes=1)

    assert _status(DUE + timedelta(days=30), resolved_at=resolved) == SlaStatus.BREACHED


def test_cancelled_ticket_has_no_sla() -> None:
    assert _status(DUE + timedelta(days=1), status=TicketStatus.CANCELLED) is None
