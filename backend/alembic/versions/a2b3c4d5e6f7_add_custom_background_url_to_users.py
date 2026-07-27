"""Add custom_background_url to users

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-26 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("custom_background_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "custom_background_url")
