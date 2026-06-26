"""add receipt item discount type

Revision ID: 20260627_0030
Revises: 20260608_0029
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260627_0030"
down_revision = "20260608_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("operation_receipt_items", "plan_receipt_items"):
        op.add_column(
            table_name,
            sa.Column("discount_type", sa.String(length=24), nullable=True),
        )


def downgrade() -> None:
    for table_name in ("plan_receipt_items", "operation_receipt_items"):
        op.drop_column(table_name, "discount_type")
