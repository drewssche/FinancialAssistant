"""Explicit package replacement confirmations; no inferred links or backfill."""
from alembic import op
import sqlalchemy as sa
revision = '20261013_0050'
down_revision = '20261013_0049'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('catalog_package_replacements',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('catalog_products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('old_variant_id', sa.Integer(), sa.ForeignKey('catalog_variants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('new_variant_id', sa.Integer(), sa.ForeignKey('catalog_variants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('old_snapshot', sa.JSON(), nullable=False),
        sa.Column('new_snapshot', sa.JSON(), nullable=False),
        sa.Column('note', sa.String(300)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'old_variant_id', name='uq_replacement_old'),
        sa.UniqueConstraint('user_id', 'new_variant_id', name='uq_replacement_new'),
        sa.CheckConstraint('old_variant_id != new_variant_id', name='ck_replacement_distinct'))
    for column in ('user_id', 'product_id'):
        op.create_index('ix_catalog_package_replacements_'+column, 'catalog_package_replacements', [column])


def downgrade():
    if op.get_bind().execute(sa.text('SELECT count(*) FROM catalog_package_replacements')).scalar():
        raise RuntimeError('Refusing to drop confirmed package replacements; keep compatible schema on rollback')
    op.drop_table('catalog_package_replacements')
