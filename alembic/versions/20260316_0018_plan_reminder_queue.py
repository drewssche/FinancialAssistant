"""add plan reminder queue

Revision ID: 20260316_0018
Revises: 20260313_0017
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260316_0018"
down_revision = "20260313_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_reminder_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["plan_id"], ["plan_operations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plan_reminder_jobs_plan_id"), "plan_reminder_jobs", ["plan_id"], unique=False)
    op.create_index(op.f("ix_plan_reminder_jobs_scheduled_for"), "plan_reminder_jobs", ["scheduled_for"], unique=False)
    op.create_index(op.f("ix_plan_reminder_jobs_status"), "plan_reminder_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_plan_reminder_jobs_user_id"), "plan_reminder_jobs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_plan_reminder_jobs_user_id"), table_name="plan_reminder_jobs")
    op.drop_index(op.f("ix_plan_reminder_jobs_status"), table_name="plan_reminder_jobs")
    op.drop_index(op.f("ix_plan_reminder_jobs_scheduled_for"), table_name="plan_reminder_jobs")
    op.drop_index(op.f("ix_plan_reminder_jobs_plan_id"), table_name="plan_reminder_jobs")
    op.drop_table("plan_reminder_jobs")
