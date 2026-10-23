from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import AuthIdentity, User, UserPreference

from app.core.config import get_settings
from app.services.telegram_admin_notifier import (
    _build_request_text,
    notify_new_pending_user,
    notify_redis_fallback_advisory,
)


class _SuccessResponse:
    def raise_for_status(self) -> None:
        return None


class _SuccessClient:
    def __init__(self, timeout: float):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json):
        return _SuccessResponse()


class _FailingClient(_SuccessClient):
    def post(self, url, json):
        raise RuntimeError("boom")


def test_notify_new_pending_user_logs_attempt_and_success(monkeypatch, caplog):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "1001")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.telegram_admin_notifier.httpx.Client", _SuccessClient)

    with caplog.at_level("INFO", logger="financial_assistant.admin_notifier"):
        notify_new_pending_user(
            user_id=7,
            display_name="Pending User",
            username="pending_user",
            telegram_id="555001",
            created_at=datetime(2026, 3, 23, 12, 0, 0),
        )

    text = caplog.text
    assert "admin_notification_event event=admin_notification_attempted" in text
    assert "admin_telegram_id=1001" in text
    assert "telegram_id=555001" in text
    assert "admin_notification_event event=admin_notification_sent" in text
    get_settings.cache_clear()


def test_notify_new_pending_user_logs_failure(monkeypatch, caplog):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "1001")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.telegram_admin_notifier.httpx.Client", _FailingClient)

    with caplog.at_level("INFO"):
        notify_new_pending_user(
            user_id=7,
            display_name="Pending User",
            username=None,
            telegram_id="555001",
            created_at=datetime(2026, 3, 23, 12, 0, 0),
        )

    text = caplog.text
    assert "admin_notification_event event=admin_notification_attempted" in text
    assert "admin_notification_event event=admin_notification_failed" in text
    assert "error=RuntimeError" in text
    assert "telegram admin notification failed for 1001: boom" in text
    get_settings.cache_clear()


def test_notify_redis_fallback_advisory_logs_attempt_and_success(monkeypatch, caplog):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "1001")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.telegram_admin_notifier.httpx.Client", _SuccessClient)

    with caplog.at_level("INFO", logger="financial_assistant.admin_notifier"):
        notify_redis_fallback_advisory(
            text="Redis advisory",
            local_cache_entries=40,
            local_fallback_reads=70,
            local_fallback_writes=30,
            dashboard_summary_p95_ms=310.0,
        )

    text = caplog.text
    assert "admin_notification_event event=redis_fallback_advisory_attempted" in text
    assert "admin_notification_event event=redis_fallback_advisory_sent" in text
    assert "local_cache_entries=40" in text
    assert "local_fallback_reads=70" in text
    get_settings.cache_clear()


@pytest.mark.parametrize("zone, expected", [
    ("Europe/Moscow", "23.10.2026 16:50 (UTC+03:00)"),
    ("America/New_York", "23.10.2026 09:50 (UTC-04:00)"),
    ("Pacific/Auckland", "24.10.2026 02:50 (UTC+13:00)"),
    ("invalid-zone", "23.10.2026 16:50 (UTC+03:00)"),
])
@pytest.mark.parametrize("tz", [None, timezone.utc])
def test_request_timestamp_uses_recipient_timezone(zone, expected, tz):
    text = _build_request_text(
        user_id=4, display_name="Applicant", username=None, telegram_id="4000",
        created_at=datetime(2026, 10, 23, 13, 50, tzinfo=tz), timezone_name=zone,
    )
    assert f"Создан: {expected}" in text


def test_request_without_timestamp():
    text = _build_request_text(
        user_id=4, display_name=None, username=None, telegram_id="4000", created_at=None,
    )
    assert "Создан: —" in text


def test_each_admin_receives_timestamp_in_saved_timezone(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "1001,1002,1003")
    get_settings.cache_clear()
    calls = []

    class CaptureClient(_SuccessClient):
        def post(self, url, json):
            calls.append(json)
            return _SuccessResponse()

    monkeypatch.setattr("app.services.telegram_admin_notifier.httpx.Client", CaptureClient)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            for user_id, prefs in [(1, {"timezone": "auto", "browser_timezone": "Europe/Moscow"}),
                                   (2, {"timezone": "America/New_York", "browser_timezone": "Europe/Moscow"})]:
                db.add(User(id=user_id, status="approved"))
                db.add(AuthIdentity(user_id=user_id, provider="telegram", provider_user_id=str(1000 + user_id)))
                db.add(UserPreference(user_id=user_id, data={"ui": prefs}))
            db.commit()
            notify_new_pending_user(
                user_id=4, display_name="Applicant", username=None, telegram_id="4000",
                created_at=datetime(2026, 10, 23, 13, 50, tzinfo=timezone.utc), db=db,
            )
        texts = {call["chat_id"]: call["text"] for call in calls}
        assert "16:50 (UTC+03:00)" in texts["1001"]
        assert "09:50 (UTC-04:00)" in texts["1002"]
        assert "16:50 (UTC+03:00)" in texts["1003"]
    finally:
        engine.dispose()
        get_settings.cache_clear()
