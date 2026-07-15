from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token
from app.db.base import Base
from app.db.models import AuthIdentity, User
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client_and_sessionmaker(monkeypatch):
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
    get_settings.cache_clear()

    test_client = TestClient(app)
    yield test_client, testing_session

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    get_settings.cache_clear()


def test_admin_telegram_id_is_auto_approved_and_marked_admin(client_and_sessionmaker, monkeypatch):
    client, testing_session = client_and_sessionmaker
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "281896361")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
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

    login_response = client.post("/api/v1/auth/telegram", json={"init_data": "test-init-data"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

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
    assert identity.provider == "telegram"
    assert identity.provider_user_id == "281896361"


def test_refresh_renews_access_token_without_resetting_session_start(client_and_sessionmaker, monkeypatch):
    client, _ = client_and_sessionmaker
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "281896361")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
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

    login_response = client.post("/api/v1/auth/telegram", json={"init_data": "test-init-data"})
    original_token = login_response.json()["access_token"]
    original_claims = decode_access_token(original_token)

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {original_token}"},
    )

    assert refresh_response.status_code == 200
    assert refresh_response.json()["expires_at"]
    refreshed_claims = decode_access_token(refresh_response.json()["access_token"])
    assert refreshed_claims["sub"] == original_claims["sub"]
    assert refreshed_claims["session_started_at"] == original_claims["session_started_at"]
    assert refreshed_claims["exp"] >= original_claims["exp"]


def test_refresh_rejects_session_past_absolute_lifetime(client_and_sessionmaker, monkeypatch):
    client, testing_session = client_and_sessionmaker
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "281896361")
    monkeypatch.setenv("APP_SESSION_MAX_HOURS", "12")
    get_settings.cache_clear()
    db = testing_session()
    user = User(display_name="Owner Admin", status="approved")
    db.add(user)
    db.flush()
    db.add(AuthIdentity(user_id=user.id, provider="telegram", provider_user_id="281896361"))
    db.commit()
    user_id = user.id
    db.close()
    old_session_start = int((datetime.now(timezone.utc) - timedelta(hours=13)).timestamp())
    token = create_access_token({"sub": str(user_id), "session_started_at": old_session_start})

    response = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Maximum session lifetime reached"


def test_refresh_rejects_unapproved_and_deleted_users(client_and_sessionmaker):
    client, testing_session = client_and_sessionmaker
    db = testing_session()
    rejected_user = User(display_name="Rejected User", status="rejected")
    db.add(rejected_user)
    db.commit()
    rejected_user_id = rejected_user.id
    db.close()
    rejected_token = create_access_token({"sub": str(rejected_user_id)})
    deleted_token = create_access_token({"sub": "999999"})

    rejected_response = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {rejected_token}"},
    )
    deleted_response = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {deleted_token}"},
    )

    assert rejected_response.status_code == 403
    assert deleted_response.status_code == 401
