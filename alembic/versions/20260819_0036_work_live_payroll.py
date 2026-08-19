"""add workday schedule for live timesheet

Revision ID: 20260819_0036
Revises: 20260818_0035
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260819_0036"
down_revision = "20260818_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "work_profiles",
        sa.Column("workday_start_time", sa.Time(), nullable=False, server_default="09:00:00"),
    )
    op.add_column(
        "work_profiles",
        sa.Column("workday_end_time", sa.Time(), nullable=False, server_default="18:00:00"),
    )
    op.add_column(
        "work_profiles",
        sa.Column("lunch_start_time", sa.Time(), nullable=False, server_default="13:00:00"),
    )
    op.add_column(
        "work_profiles",
        sa.Column("lunch_end_time", sa.Time(), nullable=False, server_default="14:00:00"),
    )


def downgrade() -> None:
    op.drop_column("work_profiles", "lunch_end_time")
    op.drop_column("work_profiles", "lunch_start_time")
    op.drop_column("work_profiles", "workday_end_time")
    op.drop_column("work_profiles", "workday_start_time")
