import importlib.util
from pathlib import Path
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_replacement_migration_empty_and_refuses_confirmed_data_loss(monkeypatch):
    spec=importlib.util.spec_from_file_location('package_replacement_migration',Path(__file__).resolve().parents[1]/'alembic/versions/20261013_0050_package_replacements.py')
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    with create_engine('sqlite+pysqlite:///:memory:').begin() as conn:
        for table in ['users','catalog_products','catalog_variants','operation_receipt_items']:
            conn.execute(text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, name TEXT)'))
            conn.execute(text(f"INSERT INTO {table} VALUES (1,'old')"))
        monkeypatch.setattr(migration,'op',Operations(MigrationContext.configure(conn)))
        migration.upgrade()
        assert conn.execute(text('SELECT count(*) FROM catalog_package_replacements')).scalar()==0
        assert conn.execute(text('SELECT name FROM operation_receipt_items')).scalar()=='old'
        migration.downgrade()
        assert 'catalog_package_replacements' not in inspect(conn).get_table_names()
        migration.upgrade()
        conn.execute(text("INSERT INTO catalog_package_replacements (id,user_id,product_id,old_variant_id,new_variant_id,effective_date,old_snapshot,new_snapshot) VALUES (1,1,1,1,2,'2026-10-02','{}','{}')"))
        with pytest.raises(RuntimeError,match='Refusing'):migration.downgrade()
        assert conn.execute(text('SELECT count(*) FROM catalog_package_replacements')).scalar()==1
