import importlib.util
import json
from pathlib import Path
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


def test_only_unambiguous_receipt_codes_are_attached_and_existing_sku_preserved(monkeypatch):
    spec=importlib.util.spec_from_file_location('internal_codes',Path(__file__).resolve().parents[1]/'alembic/versions/20261023_0055_internal_barcodes.py')
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    with create_engine('sqlite://').begin() as conn:
        for table,columns in {
            'catalog_offer_identities':'template_id INTEGER PRIMARY KEY, user_id INTEGER, retailer_code TEXT',
            'operation_item_templates':'id INTEGER, user_id INTEGER, source_id INTEGER, product_id INTEGER, is_archived BOOLEAN',
            'catalog_products':'id INTEGER, user_id INTEGER, is_archived BOOLEAN',
            'item_sources':'id INTEGER, user_id INTEGER, is_archived BOOLEAN',
            'operation_receipt_items':'user_id INTEGER, template_id INTEGER, receipt_codes JSON, line_total NUMERIC',
            'plan_receipt_items':'user_id INTEGER, template_id INTEGER, receipt_codes JSON',
        }.items():conn.execute(text(f'CREATE TABLE {table} ({columns})'))
        conn.execute(text('INSERT INTO catalog_products VALUES (1,1,false),(2,1,false),(3,2,false)'))
        conn.execute(text('INSERT INTO item_sources VALUES (5,1,false),(6,1,false),(7,2,false)'))
        conn.execute(text('INSERT INTO operation_item_templates VALUES (10,1,5,1,false),(11,1,5,2,false),(12,1,6,1,false),(13,2,7,3,false)'))
        conn.execute(text("INSERT INTO catalog_offer_identities VALUES (10,1,'1582951')"))
        a,b='22373102227750','2237310222750'
        for uid,offer,codes in [(1,10,[a,b]),(1,11,[b]),(1,12,[b]),(2,13,[a])]:
            conn.execute(text('INSERT INTO operation_receipt_items VALUES (:uid,:offer,:codes,1.35)'),dict(uid=uid,offer=offer,codes=json.dumps([dict(kind='retailer',code=c) for c in codes])))
        before=conn.execute(text('SELECT * FROM operation_receipt_items')).all()
        monkeypatch.setattr(migration,'op',Operations(MigrationContext.configure(conn)));migration.upgrade()
        rows={r.template_id:r for r in conn.execute(text('SELECT * FROM catalog_offer_identities'))}
        assert json.loads(rows[10].internal_codes)==[a] and rows[10].retailer_code=='1582951'
        assert 11 not in rows  # Same-store conflicting claims cannot be inferred.
        assert json.loads(rows[12].internal_codes)==[b]
        assert json.loads(rows[13].internal_codes)==[a]
        assert conn.execute(text('SELECT * FROM operation_receipt_items')).all()==before
        with pytest.raises(RuntimeError,match='Refusing'):migration.downgrade()
