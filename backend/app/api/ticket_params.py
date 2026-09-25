"""Query parameters of GET /tickets, collected into a TicketFilters object."""

from datetime import date
from typing import Annotated

from fastapi import Depends, Query
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

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
    q: Annotated[
        str | None,
        Query(max_length=100, description="Case-insensitive search in title and description"),
    ] = None,
    created_from: Annotated[date | None, Query(description="Created on or after (UTC)")] = None,
    created_to: Annotated[date | None, Query(description="Created on or before (UTC)")] = None,
) -> TicketFilters:
    try:
        return TicketFilters(
            status=status,
            priority=priority,
            category_id=category_id,
            assignee=assignee,
            created_by_id=created_by_id,
            q=q,
            created_from=created_from,
            created_to=created_to,
        )
    except ValidationError as exc:
        # Cross-field rules (e.g. date range) are checked by the model: report them as a
        # normal 422 validation error instead of an unexpected 500.
        raise RequestValidationError(exc.errors()) from exc


TicketFilterParams = Annotated[TicketFilters, Depends(get_ticket_filters)]
