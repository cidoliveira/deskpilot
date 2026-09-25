from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession
from app.schemas.auth import TokenRead
from app.schemas.user import UserRead, UserRegister
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: DbSession) -> UserRead:
    """Create a regular USER account. Technicians and admins are created by an admin."""
    user = user_service.register_user(db, data)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenRead)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> TokenRead:
    """OAuth2 password flow: send `username` (the e-mail) and `password` as form data."""
    return auth_service.login(db, form.username, form.password)


@router.get("/me", response_model=UserRead)
def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
