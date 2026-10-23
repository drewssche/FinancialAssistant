import importlib.util
from pathlib import Path
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_receipt_codes_migration_preserves_legacy_and_refuses_snapshot_loss(monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/20261023_0054_receipt_codes.py'
    spec = importlib.util.spec_from_file_location('receipt_codes_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with create_engine('sqlite+pysqlite:///:memory:').begin() as conn:
        for table in migration.TABLES:
            conn.execute(text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, name TEXT, quantity NUMERIC)'))
            conn.execute(text(f"INSERT INTO {table} VALUES (1, 'Старый чек', 0.242)"))
        monkeypatch.setattr(migration, 'op', Operations(MigrationContext.configure(conn)))
        migration.upgrade()
        for table in migration.TABLES:
            row = conn.execute(text(f'SELECT * FROM {table}')).mappings().one()
            assert dict(row) == dict(id=1, name='Старый чек', quantity=.242, receipt_codes=None)
        migration.downgrade()
        assert 'receipt_codes' not in {c['name'] for c in inspect(conn).get_columns(migration.TABLES[0])}
        migration.upgrade()
        conn.execute(text("UPDATE plan_receipt_items SET receipt_codes = '{\"name\":\"900 мл\"}'"))
        with pytest.raises(RuntimeError, match='Refusing'):
            migration.downgrade()
        assert 'receipt_codes' in {c['name'] for c in inspect(conn).get_columns(migration.TABLES[0])}
