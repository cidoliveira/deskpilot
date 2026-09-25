from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class PageParams:
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class PageResult[T]:
    items: Sequence[T]
    total: int
    page: int
    page_size: int


def paginate[T](session: Session, stmt: Select[tuple[T]], params: PageParams) -> PageResult[T]:
    """Run `stmt` with LIMIT/OFFSET and count the total rows matching it."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.scalar(count_stmt) or 0
    items = session.scalars(stmt.limit(params.page_size).offset(params.offset)).all()
    return PageResult(items=items, total=total, page=params.page, page_size=params.page_size)
