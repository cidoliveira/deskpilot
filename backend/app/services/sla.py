"""Resolution SLA per priority."""

from datetime import datetime, timedelta

from app.models import SlaStatus, TicketPriority, TicketStatus

SLA_HOURS: dict[TicketPriority, int] = {
    TicketPriority.CRITICAL: 4,
    TicketPriority.HIGH: 8,
    TicketPriority.MEDIUM: 24,
    TicketPriority.LOW: 48,
}

# Share of the time window after which an open ticket is "at risk".
AT_RISK_THRESHOLD = 0.8


def due_at(start: datetime, priority: TicketPriority) -> datetime:
    return start + timedelta(hours=SLA_HOURS[priority])


def sla_status(
    *,
    status: TicketStatus,
    created_at: datetime,
    due: datetime,
    resolved_at: datetime | None,
    now: datetime,
) -> SlaStatus | None:
    """None for cancelled tickets: they are out of the SLA metrics."""
    if status == TicketStatus.CANCELLED:
        return None
    if resolved_at is not None:
        return SlaStatus.MET if resolved_at <= due else SlaStatus.BREACHED
    if now > due:
        return SlaStatus.BREACHED
    at_risk_from = created_at + (due - created_at) * AT_RISK_THRESHOLD
    return SlaStatus.AT_RISK if now >= at_risk_from else SlaStatus.ON_TRACK
