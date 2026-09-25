from datetime import date
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from app.models.enums import SlaStatus, TicketPriority, TicketStatus


class TicketFilters(BaseModel):
    """Filters of GET /tickets. They narrow the tickets the user can already see and never
    widen visibility (e.g. a USER filtering by another author simply gets an empty list)."""

    model_config = ConfigDict(frozen=True)

    status: list[TicketStatus] = Field(default_factory=list)
    priority: list[TicketPriority] = Field(default_factory=list)
    category_id: int | None = None
    assignee: str | None = Field(default=None, pattern=r"^(me|none|\d+)$")
    created_by_id: int | None = None
    q: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
        | None
    ) = None
    sla_status: SlaStatus | None = None
    created_from: date | None = None
    created_to: date | None = None

    @field_validator("created_to")
    @classmethod
    def _range_is_ordered(cls, value: date | None, info: ValidationInfo) -> date | None:
        start = info.data.get("created_from")
        if value is not None and start is not None and value < start:
            raise ValueError("created_to must be on or after created_from")
        return value
