"""operation multi currency

Revision ID: 20260327_0021
Revises: 20260327_0020
Create Date: 2026-03-27 22:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_0021"
down_revision = "20260327_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("operations", sa.Column("original_amount", sa.Numeric(14, 2), nullable=True))
    op.add_column("operations", sa.Column("currency", sa.String(length=3), nullable=True))
    op.add_column("operations", sa.Column("base_currency", sa.String(length=3), nullable=True))
    op.add_column("operations", sa.Column("fx_rate", sa.Numeric(14, 6), nullable=True))

    op.execute("UPDATE operations SET original_amount = amount WHERE original_amount IS NULL")
    op.execute("UPDATE operations SET currency = 'BYN' WHERE currency IS NULL")
    op.execute("UPDATE operations SET base_currency = 'BYN' WHERE base_currency IS NULL")
    op.execute("UPDATE operations SET fx_rate = 1.000000 WHERE fx_rate IS NULL")

    op.alter_column("operations", "original_amount", nullable=False)
    op.alter_column("operations", "currency", nullable=False)
    op.alter_column("operations", "base_currency", nullable=False)
    op.alter_column("operations", "fx_rate", nullable=False)


def downgrade() -> None:
    op.drop_column("operations", "fx_rate")
    op.drop_column("operations", "base_currency")
    op.drop_column("operations", "currency")
    op.drop_column("operations", "original_amount")
