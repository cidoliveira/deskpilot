from pydantic import BaseModel

from app.models.enums import TicketPriority, TicketStatus
from app.schemas.user import UserSummary


class CategoryCount(BaseModel):
    category_id: int
    name: str
    count: int


class SlaMetrics(BaseModel):
    at_risk: int
    breached_open: int  # still open and past the due date: needs action now
    breached_resolved: int  # resolved, but late
    met: int
    # Share of resolved tickets that met the SLA; null when nothing was resolved yet.
    compliance_rate: float | None


class TechnicianWorkload(BaseModel):
    technician: UserSummary
    open: int  # OPEN, IN_PROGRESS or WAITING_USER
    resolved: int


class DashboardMetrics(BaseModel):
    total: int
    by_status: dict[TicketStatus, int]
    by_priority: dict[TicketPriority, int]
    by_category: list[CategoryCount]
    sla: SlaMetrics
    avg_resolution_hours: float | None
    by_technician: list[TechnicianWorkload]
