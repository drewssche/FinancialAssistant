"""Optional product defaults and independent purchase/plan measurements.

Revision ID: 20261012_0046
Revises: 20260907_0045
"""
from alembic import op
import sqlalchemy as sa

revision = "20261012_0046"
down_revision = "20260907_0045"
branch_labels = None
depends_on = None

TABLES = ("catalog_products", "operation_receipt_items", "plan_receipt_items")


def upgrade():
    # No defaults/backfill: historic units and package sizes remain unknown.
    for table in TABLES:
        op.add_column(table, sa.Column("sale_unit", sa.String(8), nullable=True))
        op.add_column(table, sa.Column("package_quantity", sa.Numeric(14, 3), nullable=True))
        op.add_column(table, sa.Column("package_unit", sa.String(8), nullable=True))


def downgrade():
    for table in reversed(TABLES):
        op.drop_column(table, "package_unit")
        op.drop_column(table, "package_quantity")
        op.drop_column(table, "sale_unit")
