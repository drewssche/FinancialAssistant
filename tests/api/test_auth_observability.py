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
    get_settings.cache_clear()
    return TestClient(app), testing_session


def test_pending_user_login_emits_structured_auth_events(monkeypatch, caplog):
    client, _ = _make_client(monkeypatch)
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "281896361")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.auth_service.verify_and_extract_telegram_user",
        lambda **kwargs: {
            "telegram_id": "555001",
            "display_name": "Pending User",
            "username": "pending_user",
            "avatar_url": None,
        },
    )
    monkeypatch.setattr("app.services.auth_service.notify_new_pending_user", lambda **kwargs: None)

    with caplog.at_level("INFO", logger="financial_assistant.auth"):
        response = client.post("/api/v1/auth/telegram", json={"init_data": "test-init"})

    assert response.status_code == 200
    messages = [record.message for record in caplog.records]
    assert any("auth_event event=new_user_created" in message and "status=pending" in message for message in messages)
    assert any("auth_event event=pending_user_created" in message for message in messages)
    assert any("auth_event event=login_succeeded" in message and "created=True" in message for message in messages)

    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_admin_login_emits_admin_auto_approved_and_login_events(monkeypatch, caplog):
    client, _ = _make_client(monkeypatch)
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "281896361")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.auth_service.verify_and_extract_telegram_user",
        lambda **kwargs: {
            "telegram_id": "281896361",
            "display_name": "Owner Admin",
            "username": "owner_admin",
            "avatar_url": None,
        },
    )
    monkeypatch.setattr("app.services.auth_service.notify_new_pending_user", lambda **kwargs: None)

    with caplog.at_level("INFO", logger="financial_assistant.auth"):
        response = client.post("/api/v1/auth/telegram", json={"init_data": "test-init"})

    assert response.status_code == 200
    messages = [record.message for record in caplog.records]
    assert any("auth_event event=new_user_created" in message and "status=approved" in message for message in messages)
    assert any("auth_event event=login_succeeded" in message and "status=approved" in message for message in messages)
    assert not any("auth_event event=pending_user_created" in message for message in messages)

    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_repeat_login_emits_existing_user_updated(monkeypatch, caplog):
    client, _ = _make_client(monkeypatch)
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.auth_service.verify_and_extract_telegram_user",
        lambda **kwargs: {
            "telegram_id": "777001",
            "display_name": "Repeat User",
            "username": "repeat_user",
            "avatar_url": None,
        },
    )
    monkeypatch.setattr("app.services.auth_service.notify_new_pending_user", lambda **kwargs: None)

    first = client.post("/api/v1/auth/telegram", json={"init_data": "first"})
    assert first.status_code == 200

    caplog.clear()
    with caplog.at_level("INFO", logger="financial_assistant.auth"):
        second = client.post("/api/v1/auth/telegram", json={"init_data": "second"})

    assert second.status_code == 200
    messages = [record.message for record in caplog.records]
    assert any("auth_event event=existing_user_updated" in message for message in messages)
    assert any("auth_event event=login_succeeded" in message and "created=False" in message for message in messages)

    app.dependency_overrides.clear()
    get_settings.cache_clear()
