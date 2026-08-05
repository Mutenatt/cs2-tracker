"""Drop custom_background_url from users

Revision ID: d8e1f4b7c3a5
Revises: c7d3e9f1a4b2
Create Date: 2026-08-01 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d8e1f4b7c3a5"
down_revision = "c7d3e9f1a4b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "custom_background_url")


def downgrade() -> None:
    op.add_column("users", sa.Column("custom_background_url", sa.String(), nullable=True))
