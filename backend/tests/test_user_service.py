import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.security import verify_password
from app.db.pagination import PageParams
from app.models import UserRole
from app.schemas.user import UserCreate, UserRegister, UserUpdate
from app.services import user_service
from tests.factories import make_user


def test_register_always_creates_regular_user(db_session: Session) -> None:
    data = UserRegister(name="Ana", email="Ana@Example.com", password="Str0ng-password")

    user = user_service.register_user(db_session, data)

    assert user.role == UserRole.USER
    assert user.email == "ana@example.com"
    assert verify_password("Str0ng-password", user.password_hash)


def test_email_must_be_unique_ignoring_case(db_session: Session) -> None:
    make_user(db_session, email="ana@example.com")
    data = UserRegister(name="Ana", email="ANA@example.com", password="Str0ng-password")

    with pytest.raises(ConflictError) as exc_info:
        user_service.register_user(db_session, data)
    assert exc_info.value.error == "email_already_registered"


def test_admin_can_create_technician(db_session: Session) -> None:
    data = UserCreate(
        name="Tech", email="tech@example.com", password="Str0ng-password", role="TECHNICIAN"
    )

    user = user_service.create_user(db_session, data)

    assert user.role == UserRole.TECHNICIAN


def test_get_unknown_user_raises_not_found(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        user_service.get_user(db_session, 999_999)


def test_list_users_filters_by_role_and_status(db_session: Session) -> None:
    make_user(db_session, role=UserRole.TECHNICIAN)
    make_user(db_session, role=UserRole.TECHNICIAN, is_active=False)
    make_user(db_session, role=UserRole.USER)

    result = user_service.list_users(
        db_session, PageParams(), role=UserRole.TECHNICIAN, is_active=True
    )

    assert result.total == 1
    assert result.items[0].role == UserRole.TECHNICIAN


def test_update_user_changes_only_sent_fields(db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)
    user = make_user(db_session, name="Old Name")

    updated = user_service.update_user(
        db_session, user.id, UserUpdate(role=UserRole.TECHNICIAN), acting_user=admin
    )

    assert updated.role == UserRole.TECHNICIAN
    assert updated.name == "Old Name"


def test_admin_cannot_remove_own_admin_role(db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)

    with pytest.raises(BusinessRuleError) as exc_info:
        user_service.update_user(
            db_session, admin.id, UserUpdate(role=UserRole.USER), acting_user=admin
        )
    assert exc_info.value.error == "cannot_change_own_role"


def test_admin_cannot_deactivate_self(db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)

    with pytest.raises(BusinessRuleError) as exc_info:
        user_service.update_user(
            db_session, admin.id, UserUpdate(is_active=False), acting_user=admin
        )
    assert exc_info.value.error == "cannot_deactivate_self"


def test_update_rejects_explicit_null(db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)
    user = make_user(db_session)

    with pytest.raises(BusinessRuleError):
        user_service.update_user(db_session, user.id, UserUpdate(name=None), acting_user=admin)
