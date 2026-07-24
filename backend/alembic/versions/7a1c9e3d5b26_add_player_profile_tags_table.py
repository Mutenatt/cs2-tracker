"""add player_profile_tags table

Revision ID: 7a1c9e3d5b26
Revises: 3f967f7effd5
Create Date: 2026-07-23 01:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7a1c9e3d5b26"
down_revision: str | None = "3f967f7effd5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "player_profile_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("steamid", sa.String(), nullable=False),
        sa.Column("tag_id", sa.String(), nullable=False),
        sa.Column("detalle", sa.JSON(), nullable=True),
        sa.Column("calculado_en", sa.String(), nullable=False),
        sa.Column("ventana_partidas", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["steamid"], ["players.steamid"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("player_profile_tags", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("idx_ppt_steamid"), ["steamid"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("player_profile_tags", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("idx_ppt_steamid"))

    op.drop_table("player_profile_tags")
