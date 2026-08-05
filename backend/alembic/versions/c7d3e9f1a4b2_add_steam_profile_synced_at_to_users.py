"""Merge heads + add steam_profile_synced_at to users

Revision ID: c7d3e9f1a4b2
Revises: a1c4e8f2b673, a2b3c4d5e6f7
Create Date: 2026-07-31 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c7d3e9f1a4b2"
down_revision = ("a1c4e8f2b673", "a2b3c4d5e6f7")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("steam_profile_synced_at", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "steam_profile_synced_at")
