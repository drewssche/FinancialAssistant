"""debt multi currency

Revision ID: 20260328_0023
Revises: 20260328_0022
Create Date: 2026-03-28 16:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260328_0023"
down_revision = "20260328_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("debts", sa.Column("original_principal", sa.Numeric(14, 2), nullable=True))
    op.add_column("debts", sa.Column("currency", sa.String(length=8), nullable=True))
    op.add_column("debts", sa.Column("base_currency", sa.String(length=8), nullable=True))
    op.execute("UPDATE debts SET original_principal = principal WHERE original_principal IS NULL")
    op.execute("UPDATE debts SET currency = 'BYN' WHERE currency IS NULL")
    op.execute("UPDATE debts SET base_currency = 'BYN' WHERE base_currency IS NULL")
    op.alter_column("debts", "original_principal", nullable=False)
    op.alter_column("debts", "currency", nullable=False)
    op.alter_column("debts", "base_currency", nullable=False)
    op.create_index("ix_debts_currency", "debts", ["currency"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_debts_currency", table_name="debts")
    op.drop_column("debts", "base_currency")
    op.drop_column("debts", "currency")
    op.drop_column("debts", "original_principal")
