"""add global_metric_stats table

Revision ID: b8e5a1c47f92
Revises: 9d4b2f7a6c31
Create Date: 2026-07-23 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8e5a1c47f92"
down_revision: str | None = "9d4b2f7a6c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "global_metric_stats",
        sa.Column("metric", sa.String(), nullable=False),
        sa.Column("p25", sa.Float(), nullable=False),
        sa.Column("p50", sa.Float(), nullable=False),
        sa.Column("p75", sa.Float(), nullable=False),
        sa.Column("p90", sa.Float(), nullable=False),
        sa.Column("n_players", sa.Integer(), nullable=False),
        sa.Column("calculado_en", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("metric"),
    )


def downgrade() -> None:
    op.drop_table("global_metric_stats")
