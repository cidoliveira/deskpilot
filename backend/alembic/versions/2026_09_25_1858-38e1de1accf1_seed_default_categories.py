"""seed default categories

Reference data needed in every environment, so it lives in a migration
(demo users/tickets do not). The table is described inline instead of importing
the ORM model: migrations must keep working even after the model changes.

Revision ID: 38e1de1accf1
Revises: f29b37dcdf32
Create Date: 2026-09-25 18:58:07.380447

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "38e1de1accf1"
down_revision: str | Sequence[str] | None = "f29b37dcdf32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

categories = sa.table(
    "categories",
    sa.column("name", sa.String),
    sa.column("description", sa.String),
)

DEFAULT_CATEGORIES = [
    ("Hardware", "Computers, monitors, peripherals and other physical equipment"),
    ("Software", "Installation, errors and licenses of applications"),
    ("Network", "Internet, Wi-Fi, VPN and connectivity problems"),
    ("Access", "Accounts, passwords, permissions and system access"),
    ("Email", "Mailboxes, sending/receiving problems and distribution lists"),
    ("Printer", "Printers, scanners and print queues"),
    ("Other", "Requests that do not fit any other category"),
]


def upgrade() -> None:
    op.bulk_insert(
        categories,
        [{"name": name, "description": description} for name, description in DEFAULT_CATEGORIES],
    )


def downgrade() -> None:
    names = [name for name, _ in DEFAULT_CATEGORIES]
    op.execute(categories.delete().where(categories.c.name.in_(names)))
