"""add operation receipt items and item template history

Revision ID: 20260306_0007
Revises: 20260306_0006
Create Date: 2026-03-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260306_0007"
down_revision: Union[str, None] = "20260306_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operation_item_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_ci", sa.String(length=255), nullable=False),
        sa.Column("last_category_id", sa.Integer(), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["last_category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name_ci", name="uq_operation_item_templates_user_name_ci"),
    )
    op.create_index("ix_operation_item_templates_user_name_ci", "operation_item_templates", ["user_id", "name_ci"])
    op.create_index(
        "ix_operation_item_templates_user_use_count_last_used",
        "operation_item_templates",
        ["user_id", "use_count", "last_used_at"],
    )

    op.create_table(
        "operation_item_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("source_operation_id", sa.Integer(), nullable=True),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("recorded_at", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_operation_id"], ["operations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["operation_item_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operation_item_prices_template_recorded", "operation_item_prices", ["template_id", "recorded_at"])

    op.create_table(
        "operation_receipt_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["operation_item_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operation_receipt_items_user_operation", "operation_receipt_items", ["user_id", "operation_id"])


def downgrade() -> None:
    op.drop_index("ix_operation_receipt_items_user_operation", table_name="operation_receipt_items")
    op.drop_table("operation_receipt_items")

    op.drop_index("ix_operation_item_prices_template_recorded", table_name="operation_item_prices")
    op.drop_table("operation_item_prices")

    op.drop_index("ix_operation_item_templates_user_use_count_last_used", table_name="operation_item_templates")
    op.drop_index("ix_operation_item_templates_user_name_ci", table_name="operation_item_templates")
    op.drop_table("operation_item_templates")
