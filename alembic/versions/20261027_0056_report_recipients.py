"""Per-profile report recipients and private email verification state."""
from alembic import op
import sqlalchemy as sa
revision = '20261027_0056'
down_revision = '20261023_0055'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('financial_report_recipients',
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),primary_key=True),
        sa.Column('email_address',sa.String(254),nullable=True),
        sa.Column('activated_on',sa.Date(),nullable=True),
        sa.Column('pending_email',sa.String(254),nullable=True),
        sa.Column('code_digest',sa.String(64),nullable=True),
        sa.Column('code_expires_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('code_attempts',sa.Integer(),nullable=False),
        sa.Column('last_code_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('code_day',sa.Date(),nullable=True),
        sa.Column('code_day_count',sa.Integer(),nullable=False))


def downgrade():
    if op.get_bind().execute(sa.text('SELECT count(*) FROM financial_report_recipients')).scalar():
        raise RuntimeError('Preserve confirmed report recipients when rolling back application code')
    op.drop_table('financial_report_recipients')
