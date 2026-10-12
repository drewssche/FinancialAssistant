"""Optional variant identifiers and retailer mappings; no historical backfill."""
from alembic import op
import sqlalchemy as sa

revision = '20261013_0048'
down_revision = '20261012_0047'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('catalog_variants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('catalog_products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(160), nullable=False),
        sa.Column('sale_unit', sa.String(8)),
        sa.Column('package_quantity', sa.Numeric(14,3)),
        sa.Column('package_unit', sa.String(8)),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table('catalog_variant_codes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('variant_id', sa.Integer(), sa.ForeignKey('catalog_variants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(14), nullable=False),
        sa.Column('gtin14', sa.String(14), nullable=False),
        sa.UniqueConstraint('user_id','gtin14',name='uq_variant_codes_user_gtin'))
    op.create_table('catalog_offer_identities',
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('operation_item_templates.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('variant_id', sa.Integer(), sa.ForeignKey('catalog_variants.id', ondelete='SET NULL')),
        sa.Column('retailer_code', sa.String(160)),
        sa.Column('external_name', sa.String(320)),
        sa.Column('product_url', sa.String(2048)))
    for table, columns in [('catalog_variants',['user_id','product_id']),('catalog_variant_codes',['user_id','variant_id']),('catalog_offer_identities',['user_id','variant_id'])]:
        for column in columns:
            op.create_index(f'ix_{table}_{column}',table,[column])


def downgrade():
    bind=op.get_bind()
    for table in ('catalog_offer_identities','catalog_variant_codes','catalog_variants'):
        if bind.execute(sa.text(f'SELECT count(*) FROM {table}')).scalar():
            raise RuntimeError('Refusing to drop saved catalog identifiers; keep compatible schema on rollback')
    for table in ('catalog_offer_identities','catalog_variant_codes','catalog_variants'):
        op.drop_table(table)
