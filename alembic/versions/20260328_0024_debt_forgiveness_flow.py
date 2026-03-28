"""debt forgiveness flow

Revision ID: 20260328_0024
Revises: 20260328_0023
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260328_0024"
down_revision = "20260328_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("debts", sa.Column("closure_reason", sa.String(length=24), nullable=True))
    op.create_index(op.f("ix_debts_closure_reason"), "debts", ["closure_reason"], unique=False)
    op.create_table(
        "debt_forgivenesses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("debt_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("forgiven_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["debt_id"], ["debts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_debt_forgivenesses_debt_id"), "debt_forgivenesses", ["debt_id"], unique=False)
    op.create_index(op.f("ix_debt_forgivenesses_forgiven_date"), "debt_forgivenesses", ["forgiven_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_debt_forgivenesses_forgiven_date"), table_name="debt_forgivenesses")
    op.drop_index(op.f("ix_debt_forgivenesses_debt_id"), table_name="debt_forgivenesses")
    op.drop_table("debt_forgivenesses")
    op.drop_index(op.f("ix_debts_closure_reason"), table_name="debts")
    op.drop_column("debts", "closure_reason")
