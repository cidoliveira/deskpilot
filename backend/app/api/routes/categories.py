from fastapi import APIRouter, status

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models import UserRole
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: DbSession, current_user: CurrentUser, include_inactive: bool = False
) -> list[CategoryRead]:
    """Active categories. Admins may pass `include_inactive=true` to see retired ones."""
    show_inactive = include_inactive and current_user.role == UserRole.ADMIN
    categories = category_service.list_categories(db, include_inactive=show_inactive)
    return [CategoryRead.model_validate(category) for category in categories]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: DbSession, _: AdminUser) -> CategoryRead:
    return CategoryRead.model_validate(category_service.create_category(db, data))


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int, data: CategoryUpdate, db: DbSession, _: AdminUser
) -> CategoryRead:
    return CategoryRead.model_validate(category_service.update_category(db, category_id, data))
