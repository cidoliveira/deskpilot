"""add sla due date to tickets

A NOT NULL column cannot be added directly to a table that already has rows, so the
migration runs in three steps: add as nullable -> backfill existing tickets -> set NOT NULL.
The hours are copied here on purpose (not imported from app.services.sla): a migration
must keep producing the same result even if the SLA policy changes later.

Revision ID: d36c2224df14
Revises: 2355a1a6f2c5
Create Date: 2026-09-25 19:39:46.712754

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d36c2224df14"
down_revision: str | Sequence[str] | None = "2355a1a6f2c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE tickets SET sla_due_at = created_at + CASE priority
            WHEN 'CRITICAL' THEN INTERVAL '4 hours'
            WHEN 'HIGH' THEN INTERVAL '8 hours'
            WHEN 'MEDIUM' THEN INTERVAL '24 hours'
            ELSE INTERVAL '48 hours'
        END
        """
    )
    op.alter_column("tickets", "sla_due_at", nullable=False)
    op.create_index(op.f("ix_tickets_sla_due_at"), "tickets", ["sla_due_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tickets_sla_due_at"), table_name="tickets")
    op.drop_column("tickets", "sla_due_at")
