"""Shared FastAPI dependencies: database session, current user, role guard, pagination."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import API_V1_PREFIX
from app.core.exceptions import PermissionDeniedError
from app.db.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageParams
from app.db.session import get_db
from app.models import User, UserRole
from app.services import auth_service

DbSession = Annotated[Session, Depends(get_db)]

# tokenUrl makes the "Authorize" button in Swagger UI work with /auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_V1_PREFIX}/auth/login")


def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    return auth_service.get_user_from_token(db, token)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Dependency factory: only users with one of `roles` may call the endpoint."""

    def check_role(user: CurrentUser) -> User:
        if user.role not in roles:
            raise PermissionDeniedError("You do not have permission to perform this action")
        return user

    return check_role


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def get_page_params(
    page: Annotated[int, Query(ge=1, description="Page number, starting at 1")] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


Pagination = Annotated[PageParams, Depends(get_page_params)]
