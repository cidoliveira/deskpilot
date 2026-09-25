import math

from pydantic import BaseModel, ConfigDict, computed_field


class Page[T](BaseModel):
    """Paginated response envelope."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    page_size: int

    @computed_field
    @property
    def pages(self) -> int:
        return math.ceil(self.total / self.page_size) if self.page_size else 0
