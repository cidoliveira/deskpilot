"""Query parameters of GET /tickets, collected into a TicketFilters object."""

from typing import Annotated

from fastapi import Depends, Query

from app.models import TicketPriority, TicketStatus
from app.schemas.ticket_filters import TicketFilters


def get_ticket_filters(
    status: Annotated[
        list[TicketStatus], Query(description="Repeat to match several: ?status=OPEN&status=...")
    ] = [],  # noqa: B006 - FastAPI copies query defaults, the list is never shared
    priority: Annotated[list[TicketPriority], Query()] = [],  # noqa: B006
    category_id: int | None = None,
    assignee: Annotated[
        str | None,
        Query(pattern=r"^(me|none|\d+)$", description="`me`, `none` (unassigned) or a user id"),
    ] = None,
    created_by_id: int | None = None,
) -> TicketFilters:
    return TicketFilters(
        status=status,
        priority=priority,
        category_id=category_id,
        assignee=assignee,
        created_by_id=created_by_id,
    )


TicketFilterParams = Annotated[TicketFilters, Depends(get_ticket_filters)]
