"""Add steam_background_url to users

Revision ID: f1a2b3c4d5e6
Revises: e3a7c9d1b804
Create Date: 2026-07-25 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "e3a7c9d1b804"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("steam_background_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "steam_background_url")
