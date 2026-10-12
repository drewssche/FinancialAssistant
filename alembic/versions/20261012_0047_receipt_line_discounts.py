"""Exact paid line totals and explicit discount calculation.

Revision ID: 20261012_0047
Revises: 20261012_0046
"""
from alembic import op
import sqlalchemy as sa

revision = "20261012_0047"
down_revision = "20261012_0046"
branch_labels = None
depends_on = None
TABLES = ("operation_receipt_items", "plan_receipt_items")


def upgrade():
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("discount_mode", sa.String(8), nullable=True))
            batch.add_column(sa.Column("discount_value", sa.Numeric(16, 4), nullable=True))
            batch.add_column(sa.Column("line_subtotal", sa.Numeric(14, 2), nullable=True))
            batch.alter_column("unit_price", existing_type=sa.Numeric(14, 2), type_=sa.Numeric(18, 6), existing_nullable=False)


def downgrade():
    # Downgrade would discard authoritative calculation inputs and round prices.
    # Refuse while any new-format rows exist; forward fixes preserve financial data.
    bind = op.get_bind()
    for table in TABLES:
        if bind.execute(sa.text(f"SELECT 1 FROM {table} WHERE discount_mode IS NOT NULL LIMIT 1")).first():
            raise RuntimeError("Cannot downgrade receipt pricing while exact-discount rows exist")
    for table in reversed(TABLES):
        with op.batch_alter_table(table) as batch:
            batch.alter_column("unit_price", existing_type=sa.Numeric(18, 6), type_=sa.Numeric(14, 2), existing_nullable=False)
            batch.drop_column("line_subtotal")
            batch.drop_column("discount_value")
            batch.drop_column("discount_mode")
