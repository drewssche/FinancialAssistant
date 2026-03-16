"""add plan operations

Revision ID: 20260313_0013
Revises: 20260312_0012
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260313_0013"
down_revision = "20260312_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_operations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("confirmed_operation_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("recurrence_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("recurrence_frequency", sa.String(length=20), nullable=True),
        sa.Column("recurrence_interval", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("recurrence_end_date", sa.Date(), nullable=True),
        sa.Column("confirm_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_operation_id"], ["operations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plan_operations_user_id"), "plan_operations", ["user_id"], unique=False)
    op.create_index(op.f("ix_plan_operations_confirmed_operation_id"), "plan_operations", ["confirmed_operation_id"], unique=False)
    op.create_index(op.f("ix_plan_operations_kind"), "plan_operations", ["kind"], unique=False)
    op.create_index(op.f("ix_plan_operations_scheduled_date"), "plan_operations", ["scheduled_date"], unique=False)
    op.create_index(op.f("ix_plan_operations_status"), "plan_operations", ["status"], unique=False)

    op.create_table(
        "plan_receipt_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("shop_name", sa.String(length=160), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["plan_operations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plan_receipt_items_user_id"), "plan_receipt_items", ["user_id"], unique=False)
    op.create_index(op.f("ix_plan_receipt_items_plan_id"), "plan_receipt_items", ["plan_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_plan_receipt_items_plan_id"), table_name="plan_receipt_items")
    op.drop_index(op.f("ix_plan_receipt_items_user_id"), table_name="plan_receipt_items")
    op.drop_table("plan_receipt_items")
    op.drop_index(op.f("ix_plan_operations_status"), table_name="plan_operations")
    op.drop_index(op.f("ix_plan_operations_scheduled_date"), table_name="plan_operations")
    op.drop_index(op.f("ix_plan_operations_kind"), table_name="plan_operations")
    op.drop_index(op.f("ix_plan_operations_confirmed_operation_id"), table_name="plan_operations")
    op.drop_index(op.f("ix_plan_operations_user_id"), table_name="plan_operations")
    op.drop_table("plan_operations")
