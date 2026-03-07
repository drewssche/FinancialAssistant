"""add receipt item shop fields

Revision ID: 20260306_0008
Revises: 20260306_0007
Create Date: 2026-03-06 19:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260306_0008"
down_revision = "20260306_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("operation_item_templates", sa.Column("shop_name", sa.Text(), nullable=True))
    op.add_column("operation_item_templates", sa.Column("shop_name_ci", sa.String(length=255), nullable=True))
    op.create_index(
        "ix_operation_item_templates_shop_name_ci",
        "operation_item_templates",
        ["shop_name_ci"],
        unique=False,
    )
    op.add_column("operation_receipt_items", sa.Column("shop_name", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("operation_receipt_items", "shop_name")
    op.drop_index("ix_operation_item_templates_shop_name_ci", table_name="operation_item_templates")
    op.drop_column("operation_item_templates", "shop_name_ci")
    op.drop_column("operation_item_templates", "shop_name")
