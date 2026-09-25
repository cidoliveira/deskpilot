from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.db.pagination import PageParams, PageResult, paginate
from app.models import User, UserRole
from app.schemas.user import UserCreate, UserRegister, UserUpdate


def _email_taken() -> ConflictError:
    return ConflictError("E-mail already registered", error="email_already_registered")


def get_user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found", error="user_not_found")
    return user


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email.strip().lower()))


def create_user(session: Session, data: UserCreate) -> User:
    if get_user_by_email(session, data.email) is not None:
        raise _email_taken()

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        # Two requests registering the same e-mail at the same time.
        session.rollback()
        raise _email_taken() from exc
    session.refresh(user)
    return user


def register_user(session: Session, data: UserRegister) -> User:
    """Self-registration: the role is always USER, whatever the client sends."""
    return create_user(session, UserCreate(**data.model_dump(), role=UserRole.USER))


def list_users(
    session: Session,
    params: PageParams,
    *,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> PageResult[User]:
    stmt = select(User).order_by(User.name, User.id)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    return paginate(session, stmt, params)


def update_user(session: Session, user_id: int, data: UserUpdate, *, acting_user: User) -> User:
    user = get_user(session, user_id)
    changes = data.model_dump(exclude_unset=True)

    null_fields = [field for field, value in changes.items() if value is None]
    if null_fields:
        raise BusinessRuleError(
            f"Fields cannot be null: {', '.join(null_fields)}", error="invalid_null_value"
        )

    # An admin cannot lock themselves out (and the system out of its last admin).
    if user.id == acting_user.id:
        if changes.get("role", UserRole.ADMIN) != UserRole.ADMIN:
            raise BusinessRuleError(
                "You cannot remove your own admin role", error="cannot_change_own_role"
            )
        if changes.get("is_active") is False:
            raise BusinessRuleError(
                "You cannot deactivate your own account", error="cannot_deactivate_self"
            )

    for field, value in changes.items():
        setattr(user, field, value)

    session.commit()
    session.refresh(user)
    return user
