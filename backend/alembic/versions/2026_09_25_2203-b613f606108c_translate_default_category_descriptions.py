"""translate default category descriptions

The interface is in PT-BR, but the seeded descriptions were in English. Only rows that
still hold the original seeded text are changed, so descriptions edited by an admin are
never overwritten (same in the downgrade).

Revision ID: b613f606108c
Revises: d36c2224df14
Create Date: 2026-09-25 22:03:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b613f606108c"
down_revision: str | Sequence[str] | None = "d36c2224df14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

categories = sa.table(
    "categories",
    sa.column("name", sa.String),
    sa.column("description", sa.String),
)

# name: (original English description, PT-BR description)
DESCRIPTIONS = {
    "Hardware": (
        "Computers, monitors, peripherals and other physical equipment",
        "Computadores, monitores, periféricos e outros equipamentos",
    ),
    "Software": (
        "Installation, errors and licenses of applications",
        "Instalação, erros e licenças de programas",
    ),
    "Network": (
        "Internet, Wi-Fi, VPN and connectivity problems",
        "Internet, Wi-Fi, VPN e problemas de conexão",
    ),
    "Access": (
        "Accounts, passwords, permissions and system access",
        "Contas, senhas, permissões e acesso a sistemas",
    ),
    "Email": (
        "Mailboxes, sending/receiving problems and distribution lists",
        "Caixas de e-mail, envio e recebimento e listas de distribuição",
    ),
    "Printer": (
        "Printers, scanners and print queues",
        "Impressoras, scanners e filas de impressão",
    ),
    "Other": (
        "Requests that do not fit any other category",
        "Pedidos que não se encaixam em outra categoria",
    ),
}


def _replace(pick_old: int, pick_new: int) -> None:
    for name, texts in DESCRIPTIONS.items():
        op.execute(
            categories.update()
            .where(categories.c.name == name, categories.c.description == texts[pick_old])
            .values(description=texts[pick_new])
        )


def upgrade() -> None:
    _replace(pick_old=0, pick_new=1)


def downgrade() -> None:
    _replace(pick_old=1, pick_new=0)
