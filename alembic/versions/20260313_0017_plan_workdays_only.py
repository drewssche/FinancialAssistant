"""add plan daily workdays-only rule

Revision ID: 20260313_0017
Revises: 20260313_0016
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260313_0017"
down_revision = "20260313_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plan_operations", sa.Column("recurrence_workdays_only", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("plan_operations", "recurrence_workdays_only")
