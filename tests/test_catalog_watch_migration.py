import importlib.util
from pathlib import Path
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_watch_migration_preserves_purchases_and_blocks_lossy_downgrade(monkeypatch):
    spec=importlib.util.spec_from_file_location('watch_migration',Path(__file__).resolve().parents[1]/'alembic/versions/20261016_0051_catalog_watches.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    with create_engine('sqlite+pysqlite:///:memory:').begin() as conn:
        for t in ['users','catalog_products','operation_item_templates','operation_receipt_items']:
            conn.execute(text(f'CREATE TABLE {t} (id INTEGER PRIMARY KEY, name TEXT)'))
            conn.execute(text(f"INSERT INTO {t} VALUES (1,'old')"))
        monkeypatch.setattr(m,'op',Operations(MigrationContext.configure(conn)))
        m.upgrade()
        assert conn.execute(text('SELECT count(*) FROM catalog_watches')).scalar()==0
        assert conn.execute(text('SELECT name FROM operation_receipt_items')).scalar()=='old'
        m.downgrade();assert 'catalog_watches' not in inspect(conn).get_table_names()
        m.upgrade()
        conn.execute(text('INSERT INTO catalog_watches (product_id,user_id,enabled) VALUES (1,1,true)'))
        with pytest.raises(RuntimeError,match='Keep compatible'):m.downgrade()
        assert conn.execute(text('SELECT count(*) FROM catalog_watches')).scalar()==1
