from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models.enums import TicketPriority, TicketStatus
from app.schemas.category import CategorySummary
from app.schemas.user import UserSummary

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=200)]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=10, max_length=10_000)
]


class TicketCreate(BaseModel):
    """Status, assignee and resolution are never set on creation (extra fields rejected)."""

    model_config = ConfigDict(extra="forbid")

    title: Title
    description: Description
    category_id: int
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    """Edits the ticket content only. Status, priority and assignee have dedicated
    endpoints because each one has its own permissions, rules and history event."""

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    description: Description | None = None
    category_id: int | None = None


class TicketSummary(BaseModel):
    """Ticket as shown in lists (no long text fields)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: TicketStatus
    priority: TicketPriority
    category: CategorySummary
    created_by: UserSummary
    assigned_to: UserSummary | None
    created_at: datetime
    updated_at: datetime


class TicketRead(TicketSummary):
    description: str
    resolution: str | None
    resolved_at: datetime | None
    closed_at: datetime | None


class TicketActionsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    can_edit: bool
    can_claim: bool
    can_assign: bool
    can_change_priority: bool
    can_comment: bool
    allowed_transitions: list[TicketStatus]


class TicketDetail(TicketRead):
    """Single-ticket response: the ticket plus what the current user may do with it."""

    allowed_actions: TicketActionsRead


Resolution = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=10, max_length=10_000)
]


class TicketStatusUpdate(BaseModel):
    """`resolution` is required when moving to RESOLVED and rejected otherwise."""

    model_config = ConfigDict(extra="forbid")

    status: TicketStatus
    resolution: Resolution | None = None


class TicketAssigneeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignee_id: int


class TicketPriorityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: TicketPriority
