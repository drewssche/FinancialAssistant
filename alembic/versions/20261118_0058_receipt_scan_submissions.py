"""Remember confirmed scan requests atomically with their expenses."""
from alembic import op
import sqlalchemy as sa

revision = "20261118_0058"
down_revision = "20261114_0057"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "receipt_scan_submissions",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("request_key", sa.String(36), primary_key=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("operation_id", sa.Integer(), sa.ForeignKey("operations.id", ondelete="SET NULL")),
    )
    op.create_index("ix_receipt_scan_submissions_operation_id", "receipt_scan_submissions", ["operation_id"])


def downgrade():
    op.drop_table("receipt_scan_submissions")
