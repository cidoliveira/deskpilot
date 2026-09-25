from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.user import UserSummary

Message = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Message


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author: UserSummary
    message: str
    created_at: datetime
