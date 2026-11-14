"""Store catalog, purchase and plan tags, including immutable receipt and event snapshots."""
import sqlalchemy as sa
from alembic import op

revision = "20261114_0057"
down_revision = "20261027_0056"
branch_labels = None
depends_on = None

TABLES = ("catalog_products", "operations", "plan_operations", "operation_receipt_items",
          "plan_receipt_items", "plan_operation_events")


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("tags", sa.Text(), nullable=False, server_default=""))


def downgrade():
    for table in reversed(TABLES):
        op.drop_column(table, "tags")
