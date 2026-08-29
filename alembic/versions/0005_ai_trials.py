"""users.ai_trials_used and ai_trials_period

Revision ID: 0005_ai_trials
Revises: 0004_user_role
Create Date: 2026-08-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_ai_trials"
down_revision: Union[str, None] = "0004_user_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("ai_trials_used", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("ai_trials_period", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "ai_trials_period")
    op.drop_column("users", "ai_trials_used")
