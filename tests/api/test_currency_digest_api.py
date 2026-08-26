from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.v1.currency as currency_api
from app.api.deps import get_current_user_id
from app.db.base import Base
from app.db.models import ActivityEvent, AuthIdentity, FxRateSnapshot, User, UserPreference
from app.db.session import get_db
from app.main import app


def _override_current_user_id() -> int:
    return 1


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
    app.dependency_overrides[get_current_user_id] = _override_current_user_id
    monkeypatch.setattr(
        currency_api,
        "get_settings",
        lambda: SimpleNamespace(
            telegram_bot_token="test-token",
            telegram_bot_poll_timeout_seconds=25,
        ),
    )

    yield TestClient(app), testing_session

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _seed_user(testing_session, *, telegram: bool = True, tracked=None, digest_enabled=False):
    db = testing_session()
    db.add(User(id=1, display_name="Tester", status="active"))
    db.add(User(id=2, display_name="Other", status="active"))
    if telegram:
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500"))
    db.add(AuthIdentity(user_id=2, provider="telegram", provider_user_id="200500"))
    db.add(
        UserPreference(
            user_id=1,
            preferences_version=1,
            data={
                "currency": {
                    "tracked_currencies": ["USD"] if tracked is None else tracked,
                    "telegram_digest_enabled": digest_enabled,
                    "telegram_digest_time": "00:00",
                    "telegram_digest_chart_enabled": False,
                },
                "ui": {"timezone": "UTC", "currency": "BYN"},
            },
        )
    )
    db.add(
        FxRateSnapshot(
            user_id=1,
            currency="USD",
            rate=Decimal("3.25"),
            rate_date=date(2026, 8, 26),
            source="nbrb_auto_unit",
        )
    )
    db.commit()
    db.close()


def test_manual_digest_endpoint_sends_current_users_cached_digest(client_and_sessionmaker, monkeypatch):
    client, testing_session = client_and_sessionmaker
    _seed_user(testing_session, digest_enabled=False)
    deliveries = []

    def _send(**kwargs):  # noqa: ANN003
        assert kwargs["token"] == "test-token"
        deliveries.append(kwargs["delivery"])
        return "text"

    monkeypatch.setattr(currency_api, "send_currency_digest_delivery_sync", _send)

    response = client.post(
        "/api/v1/currency/telegram-digest/send",
        json={"chat_id": "200500", "user_id": 2},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "sent"
    assert payload["delivery_format"] == "text"
    assert payload["scheduled_slot_consumed"] is False
    assert payload["tracked_currencies"] == ["USD"]
    assert payload["audit_recorded"] is True
    assert payload["message"] == "Валютный дайджест успешно отправлен в Telegram"
    assert deliveries[0].chat_id == "100500"
    assert "USD: курс НБРБ 3.2500" in deliveries[0].text

    db = testing_session()
    activity = db.query(ActivityEvent).one()
    assert activity.metadata_json["delivery_trigger"] == "manual"
    assert activity.source == "web"
    db.close()


def test_manual_digest_endpoint_requires_authentication(client_and_sessionmaker):
    client, _testing_session = client_and_sessionmaker
    app.dependency_overrides.pop(get_current_user_id, None)
    try:
        response = client.post("/api/v1/currency/telegram-digest/send")
    finally:
        app.dependency_overrides[get_current_user_id] = _override_current_user_id

    assert response.status_code == 401


def test_manual_digest_endpoint_consumes_due_scheduled_slot(client_and_sessionmaker, monkeypatch):
    client, testing_session = client_and_sessionmaker
    _seed_user(testing_session, digest_enabled=True)
    monkeypatch.setattr(
        currency_api,
        "send_currency_digest_delivery_sync",
        lambda **kwargs: "photo",
    )

    response = client.post("/api/v1/currency/telegram-digest/send")

    assert response.status_code == 200, response.text
    assert response.json()["scheduled_slot_consumed"] is True
    db = testing_session()
    preference = db.get(UserPreference, 1)
    assert preference.data["currency"]["last_digest_sent_on"]
    db.close()


def test_manual_digest_endpoint_requires_linked_telegram(client_and_sessionmaker):
    client, testing_session = client_and_sessionmaker
    _seed_user(testing_session, telegram=False)

    response = client.post("/api/v1/currency/telegram-digest/send")

    assert response.status_code == 409
    assert "не привязан Telegram" in response.json()["detail"]


def test_manual_digest_endpoint_requires_tracked_currency(client_and_sessionmaker):
    client, testing_session = client_and_sessionmaker
    _seed_user(testing_session, tracked=[])

    response = client.post("/api/v1/currency/telegram-digest/send")

    assert response.status_code == 422
    assert "отслеживаемую валюту" in response.json()["detail"]


def test_manual_digest_endpoint_rejects_parallel_delivery(client_and_sessionmaker, monkeypatch):
    client, testing_session = client_and_sessionmaker
    _seed_user(testing_session)

    @contextmanager
    def _busy_lock(*args, **kwargs):  # noqa: ANN002, ANN003
        yield False

    monkeypatch.setattr(currency_api, "try_background_job_lock", _busy_lock)

    response = client.post("/api/v1/currency/telegram-digest/send")

    assert response.status_code == 409
    assert response.json()["detail"] == "Валютный дайджест уже отправляется"


def test_manual_digest_endpoint_maps_transport_failure_without_leaking_details(
    client_and_sessionmaker,
    monkeypatch,
):
    client, testing_session = client_and_sessionmaker
    _seed_user(testing_session)

    def _fail(**kwargs):  # noqa: ANN003
        raise RuntimeError("secret Telegram provider response")

    monkeypatch.setattr(currency_api, "send_currency_digest_delivery_sync", _fail)

    response = client.post("/api/v1/currency/telegram-digest/send")

    assert response.status_code == 502
    assert response.json()["detail"] == "Не удалось отправить валютный дайджест в Telegram"
    assert "secret" not in response.text


def test_manual_digest_endpoint_reports_ambiguous_timeout_without_encouraging_retry(
    client_and_sessionmaker,
    monkeypatch,
):
    client, testing_session = client_and_sessionmaker
    _seed_user(testing_session, digest_enabled=True)

    def _timeout(**kwargs):  # noqa: ANN003
        request = httpx.Request("POST", "https://api.telegram.org/sendPhoto")
        raise httpx.ReadTimeout("response timed out", request=request)

    monkeypatch.setattr(currency_api, "send_currency_digest_delivery_sync", _timeout)

    response = client.post("/api/v1/currency/telegram-digest/send")

    assert response.status_code == 504
    detail = response.json()["detail"]
    assert "не подтвердил отправку" in detail
    assert "Проверьте чат перед повторной" in detail
    db = testing_session()
    assert db.query(ActivityEvent).count() == 0
    preference = db.get(UserPreference, 1)
    assert preference.data["currency"]["last_digest_sent_on"]
    db.close()


def test_manual_digest_endpoint_reports_sent_when_audit_persistence_fails(
    client_and_sessionmaker,
    monkeypatch,
):
    client, testing_session = client_and_sessionmaker
    _seed_user(testing_session, digest_enabled=True)
    monkeypatch.setattr(
        currency_api,
        "send_currency_digest_delivery_sync",
        lambda **kwargs: "text",
    )

    def _fail_audit(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        currency_api.TelegramCurrencyDigestBotService,
        "mark_manual_delivery_sent",
        _fail_audit,
    )

    response = client.post("/api/v1/currency/telegram-digest/send")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "sent"
    assert payload["audit_recorded"] is False
    assert payload["scheduled_slot_consumed"] is False
    assert "Дайджест отправлен в Telegram" in payload["message"]
    assert "повторная отправка по расписанию" in payload["message"]


def test_manual_digest_endpoint_reports_unconfigured_bot(client_and_sessionmaker, monkeypatch):
    client, testing_session = client_and_sessionmaker
    _seed_user(testing_session)
    monkeypatch.setattr(
        currency_api,
        "get_settings",
        lambda: SimpleNamespace(
            telegram_bot_token="change_me",
            telegram_bot_poll_timeout_seconds=25,
        ),
    )

    response = client.post("/api/v1/currency/telegram-digest/send")

    assert response.status_code == 503
    assert response.json()["detail"] == "Отправка в Telegram сейчас не настроена"
