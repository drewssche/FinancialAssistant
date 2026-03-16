"""extend plan recurrence rules

Revision ID: 20260313_0016
Revises: 20260313_0015
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260313_0016"
down_revision = "20260313_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plan_operations", sa.Column("recurrence_weekdays", sa.String(length=32), nullable=True))
    op.add_column("plan_operations", sa.Column("recurrence_month_end", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("plan_operations", "recurrence_month_end")
    op.drop_column("plan_operations", "recurrence_weekdays")
