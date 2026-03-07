from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


def _make_client(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "281896361")
    get_settings.cache_clear()
    return TestClient(app), testing_session


def test_new_pending_user_triggers_admin_notification(monkeypatch):
    client, _ = _make_client(monkeypatch)
    calls = []

    monkeypatch.setattr(
        "app.services.auth_service.verify_and_extract_telegram_user",
        lambda **kwargs: {
            "telegram_id": "555001",
            "display_name": "Pending User",
            "username": "pending_user",
            "avatar_url": None,
        },
    )
    monkeypatch.setattr(
        "app.services.auth_service.notify_new_pending_user",
        lambda **kwargs: calls.append(kwargs),
    )

    response = client.post("/api/v1/auth/telegram", json={"init_data": "test-init"})
    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0]["telegram_id"] == "555001"
    assert calls[0]["username"] == "pending_user"

    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_admin_auto_approved_login_does_not_trigger_notification(monkeypatch):
    client, _ = _make_client(monkeypatch)
    calls = []

    monkeypatch.setattr(
        "app.services.auth_service.verify_and_extract_telegram_user",
        lambda **kwargs: {
            "telegram_id": "281896361",
            "display_name": "Admin Owner",
            "username": "owner_admin",
            "avatar_url": None,
        },
    )
    monkeypatch.setattr(
        "app.services.auth_service.notify_new_pending_user",
        lambda **kwargs: calls.append(kwargs),
    )

    response = client.post("/api/v1/auth/telegram", json={"init_data": "test-init"})
    assert response.status_code == 200
    assert calls == []

    app.dependency_overrides.clear()
    get_settings.cache_clear()
