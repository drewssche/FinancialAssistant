"""Opt-in retailer price watches; additive schema, no subscriptions backfilled."""
from alembic import op
import sqlalchemy as sa
revision = '20261016_0051'
down_revision = '20261013_0050'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('catalog_watches',
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('catalog_products.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('enabled_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table('catalog_offer_watches',
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('operation_item_templates.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('catalog_products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('checked_at', sa.DateTime(timezone=True)),
        sa.Column('next_check_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('error', sa.String(300)))
    op.create_table('catalog_price_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('catalog_products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('operation_item_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('telegram_sent_at', sa.DateTime(timezone=True)))
    for table, columns in [('catalog_watches', ['user_id']), ('catalog_offer_watches', ['user_id', 'product_id', 'next_check_at']), ('catalog_price_events', ['user_id', 'product_id', 'template_id'])]:
        for col in columns:
            op.create_index(f'ix_{table}_{col}', table, [col])


def downgrade():
    for table in ['catalog_price_events', 'catalog_offer_watches', 'catalog_watches']:
        if op.get_bind().execute(sa.text(f'SELECT count(*) FROM {table}')).scalar():
            raise RuntimeError('Keep compatible watch schema on rollback; contains user data')
    for table in ['catalog_price_events', 'catalog_offer_watches', 'catalog_watches']:
        op.drop_table(table)
