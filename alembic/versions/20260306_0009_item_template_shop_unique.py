"""scope operation item template uniqueness by shop

Revision ID: 20260306_0009
Revises: 20260306_0008
Create Date: 2026-03-06 23:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260306_0009"
down_revision = "20260306_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_operation_item_templates_user_name_ci", "operation_item_templates", type_="unique")
    op.drop_index("ix_operation_item_templates_user_name_ci", table_name="operation_item_templates")
    op.create_unique_constraint(
        "uq_operation_item_templates_user_name_shop_ci",
        "operation_item_templates",
        ["user_id", "name_ci", "shop_name_ci"],
    )
    op.create_index(
        "ix_operation_item_templates_user_name_shop_ci",
        "operation_item_templates",
        ["user_id", "name_ci", "shop_name_ci"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_operation_item_templates_user_name_shop_ci", table_name="operation_item_templates")
    op.drop_constraint("uq_operation_item_templates_user_name_shop_ci", "operation_item_templates", type_="unique")
    op.create_unique_constraint(
        "uq_operation_item_templates_user_name_ci",
        "operation_item_templates",
        ["user_id", "name_ci"],
    )
    op.create_index(
        "ix_operation_item_templates_user_name_ci",
        "operation_item_templates",
        ["user_id", "name_ci"],
        unique=False,
    )
