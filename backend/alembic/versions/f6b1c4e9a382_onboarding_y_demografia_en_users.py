"""onboarding y demografia en users

Revision ID: f6b1c4e9a382
Revises: e3a7c9d1b804
Create Date: 2026-07-27 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6b1c4e9a382"
down_revision: str | None = "e3a7c9d1b804"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("onboarding_completed_at", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("bot_friend_added_at", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("age_bucket", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("country", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("acquisition_channel", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("primary_goal", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("primary_goal")
        batch_op.drop_column("acquisition_channel")
        batch_op.drop_column("country")
        batch_op.drop_column("age_bucket")
        batch_op.drop_column("bot_friend_added_at")
        batch_op.drop_column("onboarding_completed_at")
