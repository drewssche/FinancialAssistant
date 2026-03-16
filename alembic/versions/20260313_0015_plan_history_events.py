"""add plan operation history events

Revision ID: 20260313_0015
Revises: 20260313_0014
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260313_0015"
down_revision = "20260313_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_operation_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("category_name", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["plan_operations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plan_operation_events_user_id"), "plan_operation_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_plan_operation_events_plan_id"), "plan_operation_events", ["plan_id"], unique=False)
    op.create_index(op.f("ix_plan_operation_events_operation_id"), "plan_operation_events", ["operation_id"], unique=False)
    op.create_index(op.f("ix_plan_operation_events_event_type"), "plan_operation_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_plan_operation_events_kind"), "plan_operation_events", ["kind"], unique=False)
    op.create_index(op.f("ix_plan_operation_events_effective_date"), "plan_operation_events", ["effective_date"], unique=False)
    op.create_index(op.f("ix_plan_operation_events_created_at"), "plan_operation_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_plan_operation_events_created_at"), table_name="plan_operation_events")
    op.drop_index(op.f("ix_plan_operation_events_effective_date"), table_name="plan_operation_events")
    op.drop_index(op.f("ix_plan_operation_events_kind"), table_name="plan_operation_events")
    op.drop_index(op.f("ix_plan_operation_events_event_type"), table_name="plan_operation_events")
    op.drop_index(op.f("ix_plan_operation_events_operation_id"), table_name="plan_operation_events")
    op.drop_index(op.f("ix_plan_operation_events_plan_id"), table_name="plan_operation_events")
    op.drop_index(op.f("ix_plan_operation_events_user_id"), table_name="plan_operation_events")
    op.drop_table("plan_operation_events")
