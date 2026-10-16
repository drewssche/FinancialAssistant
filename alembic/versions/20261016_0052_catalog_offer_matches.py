"""Persist automatic retailer matching and ambiguous choices."""
from alembic import op
import sqlalchemy as sa

revision = '20261016_0052'
down_revision = '20261016_0051'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('catalog_offer_matches',
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('operation_item_templates.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fingerprint', sa.String(64), nullable=False),
        sa.Column('state', sa.String(24), nullable=False),
        sa.Column('candidates', sa.JSON(), nullable=False),
        sa.Column('error', sa.String(300)),
        sa.Column('next_check_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    for column in ('user_id', 'next_check_at'):
        op.create_index('ix_catalog_offer_matches_' + column, 'catalog_offer_matches', [column])


def downgrade():
    if op.get_bind().execute(sa.text('SELECT count(*) FROM catalog_offer_matches')).scalar():
        raise RuntimeError('Keep matching decisions on rollback; table contains user data')
    op.drop_table('catalog_offer_matches')
