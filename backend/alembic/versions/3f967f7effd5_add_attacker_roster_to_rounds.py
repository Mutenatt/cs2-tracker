"""add attacker_roster to rounds

Revision ID: 3f967f7effd5
Revises: c4f8d2e6a1b7
Create Date: 2026-07-23 00:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3f967f7effd5"
down_revision: str | None = "c4f8d2e6a1b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("rounds", schema=None) as batch_op:
        batch_op.add_column(sa.Column("attacker_roster", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("rounds", schema=None) as batch_op:
        batch_op.drop_column("attacker_roster")
