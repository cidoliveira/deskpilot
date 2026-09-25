from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

CategoryName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=50)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CategoryName
    description: Description | None = None


class CategoryUpdate(BaseModel):
    """Partial update. `is_active=false` retires a category without deleting it."""

    model_config = ConfigDict(extra="forbid")

    name: CategoryName | None = None
    description: Description | None = None
    is_active: bool | None = None


class CategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CategoryRead(CategorySummary):
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
