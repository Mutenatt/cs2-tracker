"""add place to player_map_events

Revision ID: c2d9f4e8a715
Revises: b8e5a1c47f92
Create Date: 2026-07-23 12:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c2d9f4e8a715"
down_revision: str | None = "b8e5a1c47f92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("player_map_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("place", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("player_map_events", schema=None) as batch_op:
        batch_op.drop_column("place")
