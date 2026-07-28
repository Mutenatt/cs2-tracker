"""email password login

Revision ID: a1c4e8f2b673
Revises: f6b1c4e9a382
Create Date: 2026-07-28 09:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1c4e8f2b673"
down_revision: str | None = "f6b1c4e9a382"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_signups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("email_verified_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_account_signups_email"),
    )

    # NOT NULL directo: requiere correr esta migración contra una tabla
    # `users` vacía (ver plan -- se vació a propósito antes de migrar, ya
    # no se mantienen cuentas creadas bajo el sistema Steam-only viejo).
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(), nullable=False))
        batch_op.add_column(sa.Column("password_hash", sa.String(), nullable=False))
        batch_op.add_column(sa.Column("email_verified_at", sa.String(), nullable=False))
        batch_op.create_unique_constraint("uq_users_email", ["email"])


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("uq_users_email", type_="unique")
        batch_op.drop_column("email_verified_at")
        batch_op.drop_column("password_hash")
        batch_op.drop_column("email")

    op.drop_table("account_signups")
