"""add plan reminder metadata

Revision ID: 20260313_0014
Revises: 20260313_0013
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260313_0014"
down_revision = "20260313_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plan_operations", sa.Column("reminder_sent_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("plan_operations", sa.Column("last_reminded_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("plan_operations", "last_reminded_at")
    op.drop_column("plan_operations", "reminder_sent_count")
