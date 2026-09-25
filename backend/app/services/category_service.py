from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def _name_taken() -> ConflictError:
    return ConflictError("A category with this name already exists", error="category_name_taken")


def _find_by_name(session: Session, name: str) -> Category | None:
    # Case-insensitive: "network" and "Network" are the same category.
    return session.scalar(select(Category).where(func.lower(Category.name) == name.lower()))


def list_categories(session: Session, *, include_inactive: bool = False) -> Sequence[Category]:
    stmt = select(Category).order_by(Category.name)
    if not include_inactive:
        stmt = stmt.where(Category.is_active.is_(True))
    return session.scalars(stmt).all()


def get_category(session: Session, category_id: int) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise NotFoundError("Category not found", error="category_not_found")
    return category


def get_active_category(session: Session, category_id: int) -> Category:
    """Category that a ticket may use. Unknown or inactive ids are a business rule error
    (422), not a 404: the ticket request itself exists, its category field is invalid."""
    category = session.get(Category, category_id)
    if category is None or not category.is_active:
        raise BusinessRuleError("Category does not exist or is inactive", error="invalid_category")
    return category


def _commit(session: Session, category: Category) -> Category:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise _name_taken() from exc
    session.refresh(category)
    return category


def create_category(session: Session, data: CategoryCreate) -> Category:
    if _find_by_name(session, data.name) is not None:
        raise _name_taken()
    category = Category(name=data.name, description=data.description)
    session.add(category)
    return _commit(session, category)


def update_category(session: Session, category_id: int, data: CategoryUpdate) -> Category:
    category = get_category(session, category_id)
    changes = data.model_dump(exclude_unset=True)

    # `description` may be cleared with null; the other fields may not.
    null_fields = [f for f in ("name", "is_active") if f in changes and changes[f] is None]
    if null_fields:
        raise BusinessRuleError(
            f"Fields cannot be null: {', '.join(null_fields)}", error="invalid_null_value"
        )

    new_name = changes.get("name")
    if new_name is not None:
        existing = _find_by_name(session, new_name)
        if existing is not None and existing.id != category.id:
            raise _name_taken()

    for field, value in changes.items():
        setattr(category, field, value)
    return _commit(session, category)
