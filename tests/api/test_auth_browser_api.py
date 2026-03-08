import hashlib
import hmac
import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import AuthIdentity, User
from app.db.session import get_db
from app.main import app


def _build_browser_auth_payload(bot_token: str, **overrides):
    payload = {
        "id": 281896361,
        "first_name": "Owner",
        "last_name": "Admin",
        "username": "owner_admin",
        "photo_url": "https://example.com/avatar.jpg",
        "auth_date": int(time.time()),
    }
    payload.update(overrides)
    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(
            (key, value)
            for key, value in payload.items()
            if value not in (None, "")
        )
    )
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return payload


def test_browser_telegram_auth_creates_approved_admin(monkeypatch):
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

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "browser-test-token")
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "browser_test_bot")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "281896361")
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    payload = _build_browser_auth_payload("browser-test-token")

    response = client.post("/api/v1/auth/telegram/browser", json=payload)
    assert response.status_code == 200
    token = response.json()["access_token"]

    me_response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    me = me_response.json()
    assert me["status"] == "approved"
    assert me["is_admin"] is True
    assert me["username"] == "owner_admin"
    assert me["telegram_id"] == "281896361"

    db = testing_session()
    user = db.scalar(select(User).where(User.display_name == "Owner Admin"))
    identity = db.scalar(select(AuthIdentity).where(AuthIdentity.user_id == user.id))
    db.close()

    assert user is not None
    assert user.status == "approved"
    assert identity is not None
    assert identity.provider_user_id == "281896361"

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    get_settings.cache_clear()


def test_browser_telegram_auth_rejected_when_browser_login_not_configured(monkeypatch):
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

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "browser-test-token")
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "")
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    payload = _build_browser_auth_payload("browser-test-token")

    response = client.post("/api/v1/auth/telegram/browser", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Browser Telegram login is not configured"

    public_config = client.get("/api/v1/auth/public-config")
    assert public_config.status_code == 200
    assert public_config.json()["browser_login_available"] is False
    assert public_config.json()["telegram_bot_username"] is None

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    get_settings.cache_clear()
