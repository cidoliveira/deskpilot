from fastapi import APIRouter, status

from app.api.deps import AdminUser, DbSession, Pagination
from app.models import UserRole
from app.schemas.common import Page
from app.schemas.errors import error_responses
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"], responses=error_responses(401, 403, 422))


@router.get("", response_model=Page[UserRead])
def list_users(
    db: DbSession,
    _: AdminUser,
    pagination: Pagination,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> Page[UserRead]:
    result = user_service.list_users(db, pagination, role=role, is_active=is_active)
    return Page[UserRead].model_validate(result)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, db: DbSession, _: AdminUser) -> UserRead:
    return UserRead.model_validate(user_service.create_user(db, data))


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: DbSession, _: AdminUser) -> UserRead:
    return UserRead.model_validate(user_service.get_user(db, user_id))


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, data: UserUpdate, db: DbSession, admin: AdminUser) -> UserRead:
    user = user_service.update_user(db, user_id, data, acting_user=admin)
    return UserRead.model_validate(user)
