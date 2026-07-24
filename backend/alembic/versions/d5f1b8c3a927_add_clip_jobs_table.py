"""add clip_jobs table

Revision ID: d5f1b8c3a927
Revises: c2d9f4e8a715
Create Date: 2026-07-23 13:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5f1b8c3a927"
down_revision: str | None = "c2d9f4e8a715"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clip_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("steamid", sa.String(), nullable=False),
        sa.Column("match_id", sa.String(), nullable=False),
        sa.Column("round_num", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["steamid"], ["players.steamid"]),
        sa.ForeignKeyConstraint(["match_id"], ["matches.match_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("clip_jobs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("idx_clip_jobs_steamid"), ["steamid"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("clip_jobs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("idx_clip_jobs_steamid"))

    op.drop_table("clip_jobs")
