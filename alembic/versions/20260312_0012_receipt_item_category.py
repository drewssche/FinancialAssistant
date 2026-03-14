from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260312_0012"
down_revision = "20260311_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "operation_receipt_items",
        sa.Column("category_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_operation_receipt_items_category_id"),
        "operation_receipt_items",
        ["category_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_operation_receipt_items_category_id_categories",
        "operation_receipt_items",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_operation_receipt_items_category_id_categories", "operation_receipt_items", type_="foreignkey")
    op.drop_index(op.f("ix_operation_receipt_items_category_id"), table_name="operation_receipt_items")
    op.drop_column("operation_receipt_items", "category_id")
