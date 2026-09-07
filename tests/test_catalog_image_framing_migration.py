import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_framing_migration_preserves_existing_images_and_is_reversible(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "alembic/versions/20260907_0045_catalog_image_framing.py"
    spec = importlib.util.spec_from_file_location("framing_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE catalog_media_assets (id INTEGER PRIMARY KEY, thumb_bytes BLOB, detail_bytes BLOB)"))
        connection.execute(text("INSERT INTO catalog_media_assets VALUES (1, :thumb, :detail)"), {"thumb": b"old thumbnail", "detail": b"uncropped source"})
        monkeypatch.setattr(module, "op", Operations(MigrationContext.configure(connection)))
        module.upgrade()
        row = connection.execute(text("SELECT * FROM catalog_media_assets")).mappings().one()
        assert row["framing"] == "{}"
        assert row["thumb_bytes"] == b"old thumbnail"
        assert row["detail_bytes"] == b"uncropped source"
        module.downgrade()
        assert "framing" not in {column["name"] for column in inspect(connection).get_columns("catalog_media_assets")}
        assert connection.execute(text("SELECT detail_bytes FROM catalog_media_assets")).scalar_one() == b"uncropped source"
        module.upgrade()
        assert connection.execute(text("SELECT framing FROM catalog_media_assets")).scalar_one() == "{}"
    engine.dispose()
