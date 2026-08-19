from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from decimal import Decimal

import pytest
from alembic.autogenerate import compare_metadata
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from app.db.base import Base
import app.db.models  # noqa: F401  # ensure all model tables are registered


REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
ALEMBIC_VERSIONS_DIR = REPO_ROOT / "alembic" / "versions"


def _get_alembic_heads() -> list[str]:
    config = Config(str(ALEMBIC_INI))
    script = ScriptDirectory.from_config(config)
    return script.get_heads()


def test_alembic_has_a_single_head_revision():
    heads = _get_alembic_heads()

    assert len(heads) == 1


def test_all_alembic_revision_files_import_and_define_migration_hooks():
    revision_ids: set[str] = set()
    down_revisions: dict[str, str | None] = {}

    for path in sorted(ALEMBIC_VERSIONS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        module_name = f"tests.migration_check_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec and spec.loader, f"Could not load migration module {path.name}"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        revision = getattr(module, "revision", None)
        down_revision = getattr(module, "down_revision", None)
        upgrade = getattr(module, "upgrade", None)
        downgrade = getattr(module, "downgrade", None)

        assert isinstance(revision, str) and revision.strip(), f"{path.name} must define revision"
        assert revision not in revision_ids, f"Duplicate revision id {revision} in {path.name}"
        assert callable(downgrade), f"{path.name} must define downgrade()"
        assert callable(upgrade), f"{path.name} must define upgrade()"

        revision_ids.add(revision)
        down_revisions[revision] = down_revision

    assert len([revision for revision, parent in down_revisions.items() if parent is None]) == 1
    assert len(revision_ids) == len(down_revisions)

    walked_revisions = []
    current_revision = _get_alembic_heads()[0]
    while current_revision is not None:
        walked_revisions.append(current_revision)
        current_revision = down_revisions[current_revision]

    assert len(walked_revisions) == len(revision_ids)
    assert set(walked_revisions) == revision_ids


def test_sqlalchemy_metadata_matches_a_fresh_database_schema():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        diffs = compare_metadata(context, Base.metadata)

    assert diffs == []


def test_fx_policy_migration_backfills_confirmed_plan_event_from_operation():
    database_url = os.getenv("MIGRATION_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("MIGRATION_TEST_DATABASE_URL is not configured")
    assert "migration_test" in database_url, "Migration test must use a dedicated disposable database"

    config = Config(str(ALEMBIC_INI))
    command.downgrade(config, "base")
    command.upgrade(config, "20260819_0037")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (id, display_name, status)
                VALUES (901, 'Migration snapshot user', 'active')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO operations (
                    id, user_id, kind, amount, original_amount, currency,
                    base_currency, fx_rate, operation_date, note
                ) VALUES (
                    902, 901, 'expense', 808.37, 229.00, 'EUR',
                    'BYN', 3.530000, DATE '2026-08-19', 'Confirmed subscription'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO plan_operations (
                    id, user_id, confirmed_operation_id, kind, amount,
                    original_amount, currency, base_currency, scheduled_date,
                    note
                ) VALUES (
                    903, 901, 902, 'expense', 229.00,
                    229.00, 'EUR', 'BYN', DATE '2026-08-19',
                    'Confirmed subscription'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO plan_operation_events (
                    id, user_id, plan_id, operation_id, event_type, kind,
                    amount, effective_date, note
                ) VALUES (
                    904, 901, 903, 902, 'confirmed', 'expense',
                    229.00, DATE '2026-08-19', 'Confirmed subscription'
                )
                """
            )
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT amount, original_amount, currency, base_currency,
                       fx_rate, fx_rate_scale, fx_payment_mode
                  FROM plan_operation_events
                 WHERE id = 904
                """
            )
        ).mappings().one()
    engine.dispose()

    assert row["amount"] == Decimal("808.37")
    assert row["original_amount"] == Decimal("229.00")
    assert row["currency"] == "EUR"
    assert row["base_currency"] == "BYN"
    assert row["fx_rate"] == Decimal("3.530000")
    assert row["fx_rate_scale"] == 1
    assert row["fx_payment_mode"] == "valuation"


def test_complete_migration_chain_on_postgresql():
    database_url = os.getenv("MIGRATION_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("MIGRATION_TEST_DATABASE_URL is not configured")
    assert "migration_test" in database_url, "Migration test must use a dedicated disposable database"

    config = Config(str(ALEMBIC_INI))
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
