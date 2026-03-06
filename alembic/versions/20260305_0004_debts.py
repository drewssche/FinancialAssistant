"""debts domain tables

Revision ID: 20260305_0004
Revises: 20260304_0003
Create Date: 2026-03-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260305_0004"
down_revision: Union[str, None] = "20260304_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "debt_counterparties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_ci", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "name_ci", name="uq_debt_counterparties_user_name_ci"),
    )
    op.create_index("ix_debt_counterparties_user_id", "debt_counterparties", ["user_id"])
    op.create_index("ix_debt_counterparties_name_ci", "debt_counterparties", ["name_ci"])

    op.create_table(
        "debts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("counterparty_id", sa.Integer(), sa.ForeignKey("debt_counterparties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("principal", sa.Numeric(14, 2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_debts_user_id", "debts", ["user_id"])
    op.create_index("ix_debts_counterparty_id", "debts", ["counterparty_id"])
    op.create_index("ix_debts_direction", "debts", ["direction"])
    op.create_index("ix_debts_start_date", "debts", ["start_date"])
    op.create_index("ix_debts_due_date", "debts", ["due_date"])

    op.create_table(
        "debt_repayments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("debt_id", sa.Integer(), sa.ForeignKey("debts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("repayment_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_debt_repayments_debt_id", "debt_repayments", ["debt_id"])
    op.create_index("ix_debt_repayments_repayment_date", "debt_repayments", ["repayment_date"])


def downgrade() -> None:
    op.drop_index("ix_debt_repayments_repayment_date", table_name="debt_repayments")
    op.drop_index("ix_debt_repayments_debt_id", table_name="debt_repayments")
    op.drop_table("debt_repayments")

    op.drop_index("ix_debts_due_date", table_name="debts")
    op.drop_index("ix_debts_start_date", table_name="debts")
    op.drop_index("ix_debts_direction", table_name="debts")
    op.drop_index("ix_debts_counterparty_id", table_name="debts")
    op.drop_index("ix_debts_user_id", table_name="debts")
    op.drop_table("debts")

    op.drop_index("ix_debt_counterparties_name_ci", table_name="debt_counterparties")
    op.drop_index("ix_debt_counterparties_user_id", table_name="debt_counterparties")
    op.drop_table("debt_counterparties")
