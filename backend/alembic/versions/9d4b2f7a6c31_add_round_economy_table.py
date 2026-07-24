"""add round_economy table

Revision ID: 9d4b2f7a6c31
Revises: 7a1c9e3d5b26
Create Date: 2026-07-23 02:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9d4b2f7a6c31"
down_revision: str | None = "7a1c9e3d5b26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "round_economy",
        sa.Column("match_id", sa.String(), nullable=False),
        sa.Column("round_num", sa.Integer(), nullable=False),
        sa.Column("steamid", sa.String(), nullable=False),
        sa.Column("equip_value", sa.Integer(), nullable=False),
        sa.Column("cash_spent", sa.Integer(), nullable=False),
        sa.Column("start_account", sa.Integer(), nullable=False),
        sa.Column("armas_compradas", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["matches.match_id"]),
        sa.ForeignKeyConstraint(["steamid"], ["players.steamid"]),
        sa.PrimaryKeyConstraint("match_id", "round_num", "steamid"),
    )


def downgrade() -> None:
    op.drop_table("round_economy")
