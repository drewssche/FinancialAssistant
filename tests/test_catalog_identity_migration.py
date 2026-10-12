import importlib.util
from pathlib import Path
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_identity_migration_preserves_old_tables_and_refuses_data_loss(monkeypatch):
    spec=importlib.util.spec_from_file_location('identity_migration',Path(__file__).resolve().parents[1]/'alembic/versions/20261013_0048_catalog_identity.py')
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    engine=create_engine('sqlite+pysqlite:///:memory:')
    with engine.begin() as conn:
        for table in ['users','catalog_products','operation_item_templates','operation_receipt_items']:
            conn.execute(text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, name TEXT)'))
            conn.execute(text(f"INSERT INTO {table} VALUES (1,'old')"))
        monkeypatch.setattr(migration,'op',Operations(MigrationContext.configure(conn)))
        migration.upgrade()
        for table in ['users','catalog_products','operation_item_templates','operation_receipt_items']:
            assert list(conn.execute(text(f'SELECT * FROM {table}')))==[(1,'old')]
        migration.downgrade()
        assert 'catalog_variants' not in inspect(conn).get_table_names()
        migration.upgrade()
        conn.execute(text("INSERT INTO catalog_variants (id,user_id,product_id,name) VALUES (1,1,1,'900 ml')"))
        with pytest.raises(RuntimeError,match='Refusing'):
            migration.downgrade()
        assert conn.execute(text('SELECT count(*) FROM catalog_variants')).scalar()==1
