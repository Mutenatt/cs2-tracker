"""merge heads: background url branch into email/onboarding branch

Revision ID: d5302cba9d28
Revises: a1c4e8f2b673, a2b3c4d5e6f7
Create Date: 2026-07-28 21:49:36.329218
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "d5302cba9d28"
down_revision: str | None = ("a1c4e8f2b673", "a2b3c4d5e6f7")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
