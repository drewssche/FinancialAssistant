"""Optional historical package identity on operation and plan receipts."""
from alembic import op
import sqlalchemy as sa

revision = "20261013_0049"
down_revision = "20261013_0048"
branch_labels = None
depends_on = None
TABLES = ("operation_receipt_items", "plan_receipt_items")


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("variant_snapshot", sa.JSON(none_as_null=True), nullable=True))


def downgrade():
    for table in TABLES:
        if op.get_bind().execute(sa.text(f"SELECT count(*) FROM {table} WHERE variant_snapshot IS NOT NULL")).scalar():
            raise RuntimeError("Refusing to drop saved receipt variants; keep compatible schema on rollback")
    for table in TABLES:
        op.drop_column(table, "variant_snapshot")
