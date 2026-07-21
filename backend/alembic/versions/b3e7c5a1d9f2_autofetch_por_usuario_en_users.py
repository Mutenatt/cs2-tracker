"""autofetch por usuario en users

Revision ID: b3e7c5a1d9f2
Revises: 4f8498400f9a
Create Date: 2026-07-18 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3e7c5a1d9f2"
down_revision: str | None = "4f8498400f9a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("steam_auth_code", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_sharecode", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("autofetch_status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("autofetch_error", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_polled_at", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_fetched_at", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("last_fetched_at")
        batch_op.drop_column("last_polled_at")
        batch_op.drop_column("autofetch_error")
        batch_op.drop_column("autofetch_status")
        batch_op.drop_column("last_sharecode")
        batch_op.drop_column("steam_auth_code")
