"""Keep private compressed receipt photos and reviewed OCR with operations."""
from alembic import op
import sqlalchemy as sa

revision = '20261018_0053'
down_revision = '20261016_0052'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('operations', sa.Column('has_receipt_scan', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('operations', sa.Column('receipt_scan_data', sa.JSON(), nullable=True))
    op.add_column('operations', sa.Column('receipt_scan_image', sa.LargeBinary(), nullable=True))


def downgrade():
    if op.get_bind().execute(sa.text('SELECT count(*) FROM operations WHERE has_receipt_scan')).scalar():
        raise RuntimeError('Keep saved receipts on rollback; operations contain receipt data')
    for name in ('receipt_scan_image', 'receipt_scan_data', 'has_receipt_scan'):
        op.drop_column('operations', name)
