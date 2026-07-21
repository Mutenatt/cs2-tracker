"""played_at en matches

Revision ID: c4f8d2e6a1b7
Revises: b3e7c5a1d9f2
Create Date: 2026-07-18 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4f8d2e6a1b7"
down_revision: str | None = "b3e7c5a1d9f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("matches", schema=None) as batch_op:
        batch_op.add_column(sa.Column("played_at", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("matches", schema=None) as batch_op:
        batch_op.drop_column("played_at")
