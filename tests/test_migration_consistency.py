from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.db.base import Base
import app.db.models  # noqa: F401  # ensure all model tables are registered


REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
ALEMBIC_VERSIONS_DIR = REPO_ROOT / "alembic" / "versions"


def test_alembic_has_a_single_head_revision():
    config = Config(str(ALEMBIC_INI))
    script = ScriptDirectory.from_config(config)

    heads = script.get_heads()

    assert heads == ["20260316_0018"]


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
    current_revision = "20260316_0018"
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
