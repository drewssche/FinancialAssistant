"""add composite performance indexes

Revision ID: 20260306_0006
Revises: 20260305_0005
Create Date: 2026-03-06
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260306_0006"
down_revision: Union[str, None] = "20260305_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Operations hot paths: list filters/sorts + first operation date lookup.
    op.create_index(
        "ix_operations_user_operation_date_id",
        "operations",
        ["user_id", "operation_date", "id"],
    )
    op.create_index(
        "ix_operations_user_kind_operation_date_id",
        "operations",
        ["user_id", "kind", "operation_date", "id"],
    )
    op.create_index(
        "ix_operations_user_category_operation_date_id",
        "operations",
        ["user_id", "category_id", "operation_date", "id"],
    )

    # Debts hot paths: active merge candidate and due-date oriented reads.
    op.create_index(
        "ix_debts_user_counterparty_direction_start_id",
        "debts",
        ["user_id", "counterparty_id", "direction", "start_date", "id"],
    )
    op.create_index(
        "ix_debts_user_due_date",
        "debts",
        ["user_id", "due_date"],
    )

    # Categories reads are mostly ordered by name with user/kind filtering.
    op.create_index(
        "ix_categories_user_kind_name",
        "categories",
        ["user_id", "kind", "name"],
    )
    op.create_index(
        "ix_categories_system_kind_name",
        "categories",
        ["is_system", "kind", "name"],
    )


def downgrade() -> None:
    op.drop_index("ix_categories_system_kind_name", table_name="categories")
    op.drop_index("ix_categories_user_kind_name", table_name="categories")

    op.drop_index("ix_debts_user_due_date", table_name="debts")
    op.drop_index("ix_debts_user_counterparty_direction_start_id", table_name="debts")

    op.drop_index("ix_operations_user_category_operation_date_id", table_name="operations")
    op.drop_index("ix_operations_user_kind_operation_date_id", table_name="operations")
    op.drop_index("ix_operations_user_operation_date_id", table_name="operations")
