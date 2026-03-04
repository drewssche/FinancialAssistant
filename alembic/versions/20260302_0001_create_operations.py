"""create operations table

Revision ID: 20260302_0001
Revises:
Create Date: 2026-03-02 16:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260302_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("subcategory", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("account", sa.String(length=64), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operations_kind"), "operations", ["kind"], unique=False)
    op.create_index(op.f("ix_operations_occurred_on"), "operations", ["occurred_on"], unique=False)
    op.create_index(op.f("ix_operations_subcategory"), "operations", ["subcategory"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_operations_subcategory"), table_name="operations")
    op.drop_index(op.f("ix_operations_occurred_on"), table_name="operations")
    op.drop_index(op.f("ix_operations_kind"), table_name="operations")
    op.drop_table("operations")
