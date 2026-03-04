"""create categories table

Revision ID: 20260302_0002
Revises: 20260302_0001
Create Date: 2026-03-02 18:10:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260302_0002"
down_revision = "20260302_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "name", name="uq_category_kind_name"),
    )
    op.create_index(op.f("ix_categories_kind"), "categories", ["kind"], unique=False)
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_kind"), table_name="categories")
    op.drop_table("categories")
