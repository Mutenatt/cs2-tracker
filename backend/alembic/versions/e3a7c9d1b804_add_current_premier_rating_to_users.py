"""add current_premier_rating to users

Revision ID: e3a7c9d1b804
Revises: d5f1b8c3a927
Create Date: 2026-07-23 14:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e3a7c9d1b804"
down_revision: str | None = "d5f1b8c3a927"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("current_premier_rating", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("current_premier_updated_at", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("current_premier_updated_at")
        batch_op.drop_column("current_premier_rating")
