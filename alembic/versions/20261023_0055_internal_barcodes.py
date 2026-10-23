"""Store-scoped internal barcodes; recover unambiguous saved receipt codes."""
import json
import re
from collections import defaultdict
from alembic import op
import sqlalchemy as sa

revision = '20261023_0055'
down_revision = '20261023_0054'
branch_labels = None
depends_on = None


def _internal(code):
    if len(code) == 14 and code.startswith('0'):
        code = code[1:]
    if not re.fullmatch(r'2[0-9]{12,13}', code):
        return False
    total = sum(int(n) * (3 if i % 2 == 0 else 1) for i, n in enumerate(reversed(code[:-1])))
    return len(code) == 13 or (10 - total % 10) % 10 != int(code[-1])


def upgrade():
    op.add_column('catalog_offer_identities', sa.Column('internal_codes', sa.JSON(none_as_null=True), nullable=True))
    conn = op.get_bind()
    claims = defaultdict(set)
    for table in ('operation_receipt_items', 'plan_receipt_items'):
        rows = conn.execute(sa.text(f'''SELECT r.user_id, t.id AS template_id, t.source_id, r.receipt_codes
            FROM {table} r JOIN operation_item_templates t ON t.id = r.template_id AND t.user_id = r.user_id
            JOIN catalog_products p ON p.id = t.product_id AND p.user_id = r.user_id
            JOIN item_sources s ON s.id = t.source_id AND s.user_id = r.user_id
            WHERE r.receipt_codes IS NOT NULL AND NOT t.is_archived AND NOT p.is_archived AND NOT s.is_archived'''))
        for row in rows.mappings():
            codes = json.loads(row['receipt_codes']) if isinstance(row['receipt_codes'], str) else row['receipt_codes']
            for entry in codes or []:
                code = entry.get('code', '').strip()
                if _internal(code):
                    claims[(row['user_id'], row['source_id'], code)].add(row['template_id'])
    by_offer = defaultdict(list)
    for (user_id, source_id, code), offers in claims.items():
        if len(offers) == 1:
            by_offer[(user_id, next(iter(offers)))].append(code)
    identities = sa.table('catalog_offer_identities', sa.column('template_id', sa.Integer),
                          sa.column('user_id', sa.BigInteger), sa.column('internal_codes', sa.JSON))
    for (user_id, template_id), codes in by_offer.items():
        # Oversized/ambiguous histories stay untouched for explicit review.
        if len(codes) > 100:
            continue
        if conn.execute(sa.select(identities.c.template_id).where(identities.c.template_id == template_id)).first():
            conn.execute(identities.update().where(identities.c.template_id == template_id).values(internal_codes=sorted(codes)))
        else:
            conn.execute(identities.insert().values(user_id=user_id, template_id=template_id, internal_codes=sorted(codes)))


def downgrade():
    if op.get_bind().execute(sa.text('SELECT count(*) FROM catalog_offer_identities WHERE internal_codes IS NOT NULL')).scalar():
        raise RuntimeError('Refusing to drop saved internal barcodes; retain compatible schema on rollback')
    op.drop_column('catalog_offer_identities', 'internal_codes')
