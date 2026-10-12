import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_measurement_upgrade_preserves_legacy_rows_without_guessing_units(monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/20261012_0046_purchase_measurements.py'
    spec = importlib.util.spec_from_file_location('measurement_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine('sqlite+pysqlite:///:memory:')
    with engine.begin() as connection:
        for table in module.TABLES:
            connection.execute(text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, name TEXT, line_total NUMERIC)'))
            connection.execute(text(f"INSERT INTO {table} VALUES (1, 'Товар 900 г', 6.50)"))
        monkeypatch.setattr(module, 'op', Operations(MigrationContext.configure(connection)))
        module.upgrade()
        for table in module.TABLES:
            row = connection.execute(text(f'SELECT * FROM {table}')).mappings().one()
            assert row['name'] == 'Товар 900 г'
            assert row['line_total'] == 6.5
            assert all(row[key] is None for key in ('sale_unit', 'package_quantity', 'package_unit'))
        module.downgrade()
        for table in module.TABLES:
            assert len(inspect(connection).get_columns(table)) == 3
            assert connection.execute(text(f'SELECT line_total FROM {table}')).scalar_one() == 6.5
        module.upgrade()
    engine.dispose()
