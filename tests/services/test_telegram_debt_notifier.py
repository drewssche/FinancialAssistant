from datetime import date
from decimal import Decimal

from app.core.config import get_settings
from app.services.telegram_debt_notifier import notify_debt_repaid_owner


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


def test_notify_debt_repaid_owner_logs_attempt_and_success(monkeypatch, caplog):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.telegram_debt_notifier.httpx.Client", _SuccessClient)

    with caplog.at_level("INFO", logger="financial_assistant.telegram_debt"):
        notify_debt_repaid_owner(
            owner_telegram_id="100500",
            debt_id=7,
            counterparty="Мария",
            direction="borrow",
            amount=Decimal("300.00"),
            repayment_date=date(2026, 3, 23),
            note="Закрыто",
        )

    text = caplog.text
    assert "telegram_debt_event event=debt_repaid_notification_attempted" in text
    assert "telegram_debt_event event=debt_repaid_notification_sent" in text
    assert "debt_id=7" in text
    assert "owner_telegram_id=100500" in text
    get_settings.cache_clear()
