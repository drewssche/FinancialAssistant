from datetime import datetime

from app.core.config import get_settings
from app.services.telegram_admin_notifier import (
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
