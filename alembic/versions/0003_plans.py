"""plans tables + user.plan_id

Revision ID: 0003_plans
Revises: 0002_password_reset
Create Date: 2026-08-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_plans"
down_revision: Union[str, None] = "0002_password_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tagline", sa.String(length=190), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_months", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("highlighted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("popular", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("cta", sa.String(length=80), nullable=False, server_default="Choisir"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_plans_slug", "plans", ["slug"])

    op.create_table(
        "plan_limitations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("limitation_type", sa.String(length=30), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "key", name="uq_plan_limitation_key"),
    )
    op.create_index("ix_plan_limitations_plan_id", "plan_limitations", ["plan_id"])

    op.create_table(
        "plan_features",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=190), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_features_plan_id", "plan_features", ["plan_id"])

    op.add_column("users", sa.Column("plan_id", sa.Integer(), nullable=True))
    op.create_index("ix_users_plan_id", "users", ["plan_id"])
    op.create_foreign_key("fk_users_plan_id", "users", "plans", ["plan_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_users_plan_id", "users", type_="foreignkey")
    op.drop_index("ix_users_plan_id", table_name="users")
    op.drop_column("users", "plan_id")
    op.drop_table("plan_features")
    op.drop_table("plan_limitations")
    op.drop_table("plans")
