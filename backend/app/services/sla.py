"""Resolution SLA per priority.

`sla_status()` computes the status in Python (for responses) and `sla_status_condition()`
expresses the same rule in SQL (for filtering). They must stay in sync; a test checks
that both agree for every status.
"""

from datetime import datetime, timedelta

from sqlalchemy import ColumnElement, and_, func, literal, or_

from app.models import SlaStatus, Ticket, TicketPriority, TicketStatus

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


def sla_status_condition(target: SlaStatus, now: datetime) -> ColumnElement[bool]:
    """SQL twin of `sla_status()`: tickets whose SLA status is `target` at `now`."""
    now_ = literal(now)
    resolved = Ticket.resolved_at.is_not(None)
    unresolved = and_(Ticket.resolved_at.is_(None), Ticket.status != TicketStatus.CANCELLED)
    # "At risk" point in epoch seconds: plain numbers can be multiplied by the threshold
    # (multiplying an INTERVAL by a float is deprecated in SQLAlchemy).
    created_s = func.extract("epoch", Ticket.created_at)
    due_s = func.extract("epoch", Ticket.sla_due_at)
    at_risk_from_s = created_s + (due_s - created_s) * AT_RISK_THRESHOLD
    now_s = literal(now.timestamp())

    conditions = {
        SlaStatus.MET: and_(resolved, Ticket.resolved_at <= Ticket.sla_due_at),
        SlaStatus.BREACHED: or_(
            and_(resolved, Ticket.resolved_at > Ticket.sla_due_at),
            and_(unresolved, now_ > Ticket.sla_due_at),
        ),
        SlaStatus.AT_RISK: and_(unresolved, now_ <= Ticket.sla_due_at, now_s >= at_risk_from_s),
        SlaStatus.ON_TRACK: and_(unresolved, now_s < at_risk_from_s),
    }
    return conditions[target]
