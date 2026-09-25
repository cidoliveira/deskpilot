"""Aggregated metrics for the admin dashboard.

Each metric is one GROUP BY / aggregate query computed by PostgreSQL, instead of loading
tickets into Python. The optional date range applies to the ticket creation date.
[PROD] With a large history these queries would move to a reporting replica or a
pre-aggregated table refreshed periodically.
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import ColumnElement, Select, and_, func, select, true
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.models import Category, SlaStatus, Ticket, TicketPriority, TicketStatus, User
from app.schemas.dashboard import (
    CategoryCount,
    DashboardMetrics,
    SlaMetrics,
    TechnicianWorkload,
)
from app.schemas.user import UserSummary
from app.services import sla
from app.services.ticket_queries import start_of_day

ACTIVE_STATUSES = (TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_USER)


def _period(created_from: date | None, created_to: date | None) -> ColumnElement[bool]:
    if created_from and created_to and created_to < created_from:
        raise BusinessRuleError(
            "created_to must be on or after created_from", error="invalid_date_range"
        )
    conditions = []
    if created_from is not None:
        conditions.append(Ticket.created_at >= start_of_day(created_from))
    if created_to is not None:
        conditions.append(Ticket.created_at < start_of_day(created_to + timedelta(days=1)))
    return and_(*conditions) if conditions else true()


def _count(session: Session, period: ColumnElement[bool], *conditions: ColumnElement[bool]) -> int:
    stmt = select(func.count()).select_from(Ticket).where(period, *conditions)
    return session.scalar(stmt) or 0


def _counts_by(session: Session, column, period: ColumnElement[bool]) -> dict:
    rows = session.execute(select(column, func.count()).where(period).group_by(column))
    return dict(rows.all())


def _by_category(session: Session, period: ColumnElement[bool]) -> list[CategoryCount]:
    stmt: Select = (
        select(Category.id, Category.name, func.count(Ticket.id))
        .join(Ticket, Ticket.category_id == Category.id)
        .where(period)
        .group_by(Category.id, Category.name)
        .order_by(func.count(Ticket.id).desc(), Category.name)
    )
    return [CategoryCount(category_id=i, name=n, count=c) for i, n, c in session.execute(stmt)]


def _sla(session: Session, period: ColumnElement[bool], now: datetime) -> SlaMetrics:
    def count(status: SlaStatus, *extra: ColumnElement[bool]) -> int:
        # Reuses the SQL twin of the SLA rule, so dashboard and filters always agree.
        return _count(session, period, sla.sla_status_condition(status, now), *extra)

    met = count(SlaStatus.MET)
    breached_resolved = count(SlaStatus.BREACHED, Ticket.resolved_at.is_not(None))
    resolved = met + breached_resolved
    return SlaMetrics(
        at_risk=count(SlaStatus.AT_RISK),
        breached_open=count(SlaStatus.BREACHED, Ticket.resolved_at.is_(None)),
        breached_resolved=breached_resolved,
        met=met,
        compliance_rate=round(met / resolved, 4) if resolved else None,
    )


def _avg_resolution_hours(session: Session, period: ColumnElement[bool]) -> float | None:
    seconds = func.extract("epoch", Ticket.resolved_at - Ticket.created_at)
    avg = session.scalar(select(func.avg(seconds)).where(period, Ticket.resolved_at.is_not(None)))
    return None if avg is None else round(float(avg) / 3600, 2)


def _by_technician(session: Session, period: ColumnElement[bool]) -> list[TechnicianWorkload]:
    open_count = func.count().filter(Ticket.status.in_(ACTIVE_STATUSES))
    resolved_count = func.count().filter(Ticket.resolved_at.is_not(None))
    stmt = (
        select(User.id, User.name, open_count, resolved_count)
        .join(Ticket, Ticket.assigned_to_id == User.id)
        .where(period)
        .group_by(User.id, User.name)
        .order_by(open_count.desc(), User.name)
    )
    return [
        TechnicianWorkload(technician=UserSummary(id=i, name=n), open=o, resolved=r)
        for i, n, o, r in session.execute(stmt)
    ]


def get_metrics(
    session: Session,
    *,
    created_from: date | None = None,
    created_to: date | None = None,
    now: datetime | None = None,
) -> DashboardMetrics:
    now = now or datetime.now(UTC)
    period = _period(created_from, created_to)
    by_status = _counts_by(session, Ticket.status, period)
    by_priority = _counts_by(session, Ticket.priority, period)
    return DashboardMetrics(
        total=sum(by_status.values()),
        # Every status/priority is present, with 0 when there are no tickets.
        by_status={status: by_status.get(status, 0) for status in TicketStatus},
        by_priority={priority: by_priority.get(priority, 0) for priority in TicketPriority},
        by_category=_by_category(session, period),
        sla=_sla(session, period, now),
        avg_resolution_hours=_avg_resolution_hours(session, period),
        by_technician=_by_technician(session, period),
    )
