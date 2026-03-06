"""debt issuances history

Revision ID: 20260305_0005
Revises: 20260305_0004
Create Date: 2026-03-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260305_0005"
down_revision: Union[str, None] = "20260305_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "debt_issuances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("debt_id", sa.Integer(), sa.ForeignKey("debts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("issuance_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_debt_issuances_debt_id", "debt_issuances", ["debt_id"])
    op.create_index("ix_debt_issuances_issuance_date", "debt_issuances", ["issuance_date"])


def downgrade() -> None:
    op.drop_index("ix_debt_issuances_issuance_date", table_name="debt_issuances")
    op.drop_index("ix_debt_issuances_debt_id", table_name="debt_issuances")
    op.drop_table("debt_issuances")
