"""add item brands

Revision ID: 20260904_0041
Revises: 20260826_0040
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260904_0041"
down_revision = "20260826_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "item_brands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_ci", sa.String(length=320), nullable=False),
        sa.Column("accent_color", sa.String(length=7), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name_ci", name="uq_item_brands_user_name_ci"),
    )
    op.create_index(op.f("ix_item_brands_name_ci"), "item_brands", ["name_ci"], unique=False)
    op.create_index(op.f("ix_item_brands_user_id"), "item_brands", ["user_id"], unique=False)
    op.add_column("operation_item_templates", sa.Column("brand_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_operation_item_templates_brand_id_item_brands",
        "operation_item_templates",
        "item_brands",
        ["brand_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_operation_item_templates_brand_id"),
        "operation_item_templates",
        ["brand_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_operation_item_templates_brand_id"), table_name="operation_item_templates")
    op.drop_constraint(
        "fk_operation_item_templates_brand_id_item_brands",
        "operation_item_templates",
        type_="foreignkey",
    )
    op.drop_column("operation_item_templates", "brand_id")
    op.drop_index(op.f("ix_item_brands_user_id"), table_name="item_brands")
    op.drop_index(op.f("ix_item_brands_name_ci"), table_name="item_brands")
    op.drop_table("item_brands")
