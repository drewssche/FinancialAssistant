"""add debt reminder queue

Revision ID: 20260323_0019
Revises: 20260316_0018
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_0019"
down_revision = "20260316_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "debt_reminder_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("debt_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["debt_id"], ["debts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_debt_reminder_jobs_debt_id"), "debt_reminder_jobs", ["debt_id"], unique=False)
    op.create_index(op.f("ix_debt_reminder_jobs_event_type"), "debt_reminder_jobs", ["event_type"], unique=False)
    op.create_index(op.f("ix_debt_reminder_jobs_scheduled_for"), "debt_reminder_jobs", ["scheduled_for"], unique=False)
    op.create_index(op.f("ix_debt_reminder_jobs_status"), "debt_reminder_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_debt_reminder_jobs_user_id"), "debt_reminder_jobs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_debt_reminder_jobs_user_id"), table_name="debt_reminder_jobs")
    op.drop_index(op.f("ix_debt_reminder_jobs_status"), table_name="debt_reminder_jobs")
    op.drop_index(op.f("ix_debt_reminder_jobs_scheduled_for"), table_name="debt_reminder_jobs")
    op.drop_index(op.f("ix_debt_reminder_jobs_event_type"), table_name="debt_reminder_jobs")
    op.drop_index(op.f("ix_debt_reminder_jobs_debt_id"), table_name="debt_reminder_jobs")
    op.drop_table("debt_reminder_jobs")
