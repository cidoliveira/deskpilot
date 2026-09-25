import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def test_database_rejects_category_names_differing_only_in_case(db_session: Session) -> None:
    # Bypasses the service on purpose: two concurrent requests could both pass the
    # service's pre-check, so the database must enforce the rule on its own.
    with pytest.raises(IntegrityError, match="uq_categories_name_lower"), db_session.begin_nested():
        db_session.execute(text("INSERT INTO categories (name) VALUES ('NETWORK')"))


def test_different_names_are_accepted(db_session: Session) -> None:
    db_session.execute(text("INSERT INTO categories (name) VALUES ('Phones'), ('Tablets')"))
