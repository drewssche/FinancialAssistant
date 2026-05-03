"""add receipt item discount markers

Revision ID: 20260504_0028
Revises: 20260402_0027
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260504_0028"
down_revision = "20260402_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("operation_receipt_items", "plan_receipt_items"):
        op.add_column(
            table_name,
            sa.Column("is_discounted", sa.Boolean(), server_default=sa.false(), nullable=False),
        )
        op.add_column(
            table_name,
            sa.Column("regular_unit_price", sa.Numeric(14, 2), nullable=True),
        )


def downgrade() -> None:
    for table_name in ("plan_receipt_items", "operation_receipt_items"):
        op.drop_column(table_name, "regular_unit_price")
        op.drop_column(table_name, "is_discounted")
