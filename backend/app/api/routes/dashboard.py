from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, DbSession
from app.schemas.dashboard import DashboardMetrics
from app.schemas.errors import error_responses
from app.services import dashboard_service

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], responses=error_responses(401, 403, 422)
)


@router.get("/metrics", response_model=DashboardMetrics)
def get_metrics(
    db: DbSession,
    _: AdminUser,
    created_from: Annotated[date | None, Query(description="Tickets created on or after")] = None,
    created_to: Annotated[date | None, Query(description="Tickets created on or before")] = None,
) -> DashboardMetrics:
    """Admin-only metrics: volume by status, priority and category, SLA, average resolution
    time and workload per technician. The optional date range filters by creation date."""
    return dashboard_service.get_metrics(db, created_from=created_from, created_to=created_to)
