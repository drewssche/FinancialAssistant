"""Preserve printed receipt identifiers independently of catalog SKUs."""
from alembic import op
import sqlalchemy as sa

revision = "20261023_0054"
down_revision = "20261018_0053"
branch_labels = None
depends_on = None
TABLES = ("operation_receipt_items", "plan_receipt_items")


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("receipt_codes", sa.JSON(none_as_null=True), nullable=True))


def downgrade():
    for table in TABLES:
        if op.get_bind().execute(sa.text(f"SELECT count(*) FROM {table} WHERE receipt_codes IS NOT NULL")).scalar():
            raise RuntimeError("Refusing to drop saved receipt codes; keep compatible schema on rollback")
    for table in TABLES:
        op.drop_column(table, "receipt_codes")
