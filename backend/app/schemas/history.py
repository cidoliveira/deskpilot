from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import TicketAction
from app.schemas.user import UserSummary


class TicketEventRead(BaseModel):
    """One entry of the ticket timeline.

    `old_value`/`new_value` are the raw stored values; for assignments and category
    changes (stored as ids) `old_label`/`new_label` carry the current names.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    action: TicketAction
    changed_by: UserSummary
    old_value: str | None
    new_value: str | None
    old_label: str | None
    new_label: str | None
    created_at: datetime
