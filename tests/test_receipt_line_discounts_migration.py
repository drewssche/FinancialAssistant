import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_discount_migration_preserves_history_and_refuses_lossy_downgrade(monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/20261012_0047_receipt_line_discounts.py'
    spec = importlib.util.spec_from_file_location('discount_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine('sqlite+pysqlite:///:memory:')
    with engine.begin() as conn:
        for table in module.TABLES:
            conn.execute(text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, unit_price NUMERIC(14,2) NOT NULL, line_total NUMERIC(14,2))'))
            conn.execute(text(f'INSERT INTO {table} VALUES (1, 15.64, 3.78)'))
        monkeypatch.setattr(module, 'op', Operations(MigrationContext.configure(conn)))
        module.upgrade()
        for table in module.TABLES:
            row = conn.execute(text(f'SELECT * FROM {table}')).mappings().one()
            assert row['unit_price'] == 15.64 and row['line_total'] == 3.78
            assert all(row[key] is None for key in ('discount_mode', 'discount_value', 'line_subtotal'))
        module.downgrade()
        assert len(inspect(conn).get_columns(module.TABLES[0])) == 3
        module.upgrade()
        conn.execute(text("UPDATE plan_receipt_items SET discount_mode = 'final', discount_value = 3.65, line_subtotal = 3.78, unit_price = 15.082645, line_total = 3.65"))
        with pytest.raises(RuntimeError, match='Cannot downgrade'):
            module.downgrade()
        assert len(inspect(conn).get_columns(module.TABLES[0])) == 6
        assert conn.execute(text('SELECT line_total FROM plan_receipt_items')).scalar_one() == 3.65
    engine.dispose()
