"""plan multi currency

Revision ID: 20260328_0022
Revises: 20260327_0021
Create Date: 2026-03-28 12:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260328_0022"
down_revision = "20260327_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plan_operations", sa.Column("original_amount", sa.Numeric(14, 2), nullable=False, server_default="0.00"))
    op.add_column("plan_operations", sa.Column("currency", sa.String(length=3), nullable=False, server_default="BYN"))
    op.add_column("plan_operations", sa.Column("base_currency", sa.String(length=3), nullable=False, server_default="BYN"))
    op.execute("UPDATE plan_operations SET original_amount = amount WHERE original_amount = 0")
    op.alter_column("plan_operations", "original_amount", server_default=None)
    op.alter_column("plan_operations", "currency", server_default=None)
    op.alter_column("plan_operations", "base_currency", server_default=None)


def downgrade() -> None:
    op.drop_column("plan_operations", "base_currency")
    op.drop_column("plan_operations", "currency")
    op.drop_column("plan_operations", "original_amount")
