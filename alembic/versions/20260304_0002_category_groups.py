"""category groups and category-group link

Revision ID: 20260304_0002
Revises: 20260304_0001
Create Date: 2026-03-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260304_0002"
down_revision: Union[str, None] = "20260304_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "category_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("accent_color", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_category_groups_user_id", "category_groups", ["user_id"])
    op.create_index("ix_category_groups_name", "category_groups", ["name"])
    op.create_index("ix_category_groups_kind", "category_groups", ["kind"])

    op.add_column("categories", sa.Column("group_id", sa.Integer(), nullable=True))
    op.create_index("ix_categories_group_id", "categories", ["group_id"])
    op.create_foreign_key(
        "fk_categories_group_id_category_groups",
        "categories",
        "category_groups",
        ["group_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_categories_group_id_category_groups", "categories", type_="foreignkey")
    op.drop_index("ix_categories_group_id", table_name="categories")
    op.drop_column("categories", "group_id")

    op.drop_index("ix_category_groups_kind", table_name="category_groups")
    op.drop_index("ix_category_groups_name", table_name="category_groups")
    op.drop_index("ix_category_groups_user_id", table_name="category_groups")
    op.drop_table("category_groups")
