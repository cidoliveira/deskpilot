from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint names, so Alembic migrations are reproducible and
# constraints can be dropped/altered by name later.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """created_at / updated_at filled by the database, always timezone-aware (UTC)."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def enum_column(enum_class: type[StrEnum], name: str) -> Enum:
    """Store a Python enum as VARCHAR + CHECK constraint instead of a native PostgreSQL ENUM.

    Native ENUM types need manual `ALTER TYPE` migrations to add values; a CHECK
    constraint is easier to evolve with Alembic and still rejects invalid values.

    Alembic autogenerate renders this CHECK twice; in the migration keep only the
    `op.f("ck_<table>_<name>")` constraint and set `create_constraint=False` on the Enum.
    """
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=max(len(member.value) for member in enum_class) + 10,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )
