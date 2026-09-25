"""Small helpers to create test data directly in the database."""

from itertools import count

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models import Category, Ticket, TicketPriority, TicketStatus, User, UserRole

DEFAULT_PASSWORD = "Str0ng-password"
# Hashing is intentionally slow (Argon2); hash the default password only once.
_DEFAULT_PASSWORD_HASH = hash_password(DEFAULT_PASSWORD)
_sequence = count(1)


def make_user(
    session: Session,
    *,
    role: UserRole = UserRole.USER,
    email: str | None = None,
    name: str | None = None,
    password: str = DEFAULT_PASSWORD,
    is_active: bool = True,
) -> User:
    number = next(_sequence)
    password_hash = (
        _DEFAULT_PASSWORD_HASH if password == DEFAULT_PASSWORD else hash_password(password)
    )
    user = User(
        name=name or f"{role.value.title()} {number}",
        email=email or f"{role.value.lower()}{number}@example.com",
        password_hash=password_hash,
        role=role,
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    return user


def make_category(session: Session, *, name: str | None = None, is_active: bool = True) -> Category:
    category = Category(name=name or f"Category {next(_sequence)}", is_active=is_active)
    session.add(category)
    session.flush()
    return category


def make_ticket(
    session: Session,
    *,
    created_by: User,
    category: Category | None = None,
    title: str | None = None,
    description: str = "Something is not working as expected.",
    priority: TicketPriority = TicketPriority.MEDIUM,
    status: TicketStatus = TicketStatus.OPEN,
    assigned_to: User | None = None,
    resolution: str | None = None,
) -> Ticket:
    ticket = Ticket(
        title=title or f"Ticket {next(_sequence)}",
        description=description,
        category=category or make_category(session),
        priority=priority,
        status=status,
        created_by=created_by,
        assigned_to=assigned_to,
        resolution=resolution,
    )
    session.add(ticket)
    session.flush()
    return ticket


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
