"""add password reset columns on users

Revision ID: 0002_password_reset
Revises: 0001_initial
Create Date: 2026-08-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_password_reset"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("reset_code", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column("reset_code_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "reset_code_expires_at")
    op.drop_column("users", "reset_code")
