from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TicketPriority, TicketStatus


class TicketFilters(BaseModel):
    """Filters of GET /tickets. They narrow the tickets the user can already see and never
    widen visibility (e.g. a USER filtering by another author simply gets an empty list)."""

    model_config = ConfigDict(frozen=True)

    status: list[TicketStatus] = Field(default_factory=list)
    priority: list[TicketPriority] = Field(default_factory=list)
    category_id: int | None = None
    assignee: str | None = Field(default=None, pattern=r"^(me|none|\d+)$")
    created_by_id: int | None = None
