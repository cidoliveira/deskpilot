from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.pagination import PageParams, paginate
from app.models import User
from app.schemas.common import Page


class _UserItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str


def _create_users(session: Session, count: int) -> None:
    session.add_all(
        User(name=f"User {i}", email=f"user{i}@example.com", password_hash="x")
        for i in range(count)
    )
    session.flush()


def test_paginate_returns_requested_slice_and_total(db_session: Session) -> None:
    _create_users(db_session, 5)
    stmt = select(User).order_by(User.email)

    result = paginate(db_session, stmt, PageParams(page=2, page_size=2))

    assert result.total == 5
    assert [u.email for u in result.items] == ["user2@example.com", "user3@example.com"]


def test_last_page_can_be_partial(db_session: Session) -> None:
    _create_users(db_session, 5)

    result = paginate(db_session, select(User), PageParams(page=3, page_size=2))

    assert len(result.items) == 1


def test_page_schema_computes_number_of_pages(db_session: Session) -> None:
    _create_users(db_session, 5)
    result = paginate(db_session, select(User), PageParams(page=1, page_size=2))

    page = Page[_UserItem].model_validate(result)

    assert page.pages == 3
    assert page.model_dump()["pages"] == 3


def test_empty_result_has_zero_pages(db_session: Session) -> None:
    result = paginate(db_session, select(User), PageParams())

    page = Page[_UserItem].model_validate(result)

    assert page.total == 0
    assert page.pages == 0
    assert page.items == []
