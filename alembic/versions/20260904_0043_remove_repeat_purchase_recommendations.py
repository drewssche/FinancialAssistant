"""remove repeat purchase recommendations

Revision ID: 20260904_0043
Revises: 20260904_0042
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260904_0043"
down_revision = "20260904_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        "ix_operation_item_templates_recommendation_snoozed_until",
        table_name="operation_item_templates",
    )
    op.drop_index(
        "ix_operation_item_templates_recommendation_next_date",
        table_name="operation_item_templates",
    )
    op.drop_column("operation_item_templates", "recommendation_snoozed_until")
    op.drop_column("operation_item_templates", "recommendation_next_date")
    op.drop_column("operation_item_templates", "recommendation_base_quantity")
    op.drop_column("operation_item_templates", "recommendation_interval_days")
    op.drop_column("operation_item_templates", "recommendation_mode")
    op.drop_column("operation_item_templates", "recommendation_enabled")


def downgrade() -> None:
    op.add_column(
        "operation_item_templates",
        sa.Column(
            "recommendation_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "operation_item_templates",
        sa.Column(
            "recommendation_mode",
            sa.String(length=16),
            nullable=False,
            server_default="manual",
        ),
    )
    op.add_column(
        "operation_item_templates",
        sa.Column("recommendation_interval_days", sa.Integer(), nullable=True),
    )
    op.add_column(
        "operation_item_templates",
        sa.Column(
            "recommendation_base_quantity",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default="1.000",
        ),
    )
    op.add_column(
        "operation_item_templates",
        sa.Column("recommendation_next_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "operation_item_templates",
        sa.Column("recommendation_snoozed_until", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_operation_item_templates_recommendation_next_date",
        "operation_item_templates",
        ["recommendation_next_date"],
    )
    op.create_index(
        "ix_operation_item_templates_recommendation_snoozed_until",
        "operation_item_templates",
        ["recommendation_snoozed_until"],
    )
