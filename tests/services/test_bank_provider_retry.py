from datetime import datetime, timedelta, timezone
from decimal import Decimal
import socket
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

import app.services.bank_currency_rate_refresh_service as rates


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(rates, "_LAST_PROVIDER_ATTEMPT", {})
    monkeypatch.setattr(rates, "_PROVIDER_FAILURES", {})
    monkeypatch.setattr(rates, "invalidate_plans_cache", lambda _: None)
    service = rates.BankCurrencyRateRefreshService(Mock())
    monkeypatch.setattr(service, "_resolve_config", lambda **_: {"bank_codes": ["sber"], "currencies": ["EUR"]})
    service.repo = Mock()
    service.repo.get_latest_bank_rate_map.return_value = {}
    return service


def test_failed_provider_backs_off_without_overwriting_quotes(service, monkeypatch, caplog):
    fetch = Mock(side_effect=httpx.ConnectError("private error details"))
    monkeypatch.setattr(service, "_fetch_provider", fetch)
    caplog.set_level("INFO")
    for expected_minutes in [15, 30, 60, 120, 240, 360, 360]:
        rates._LAST_PROVIDER_ATTEMPT.clear()  # Simulate the scheduled retry becoming due.
        assert service.refresh_user_selected_rates(user_id=1) == []
        assert rates._provider_retry_minutes("sber") == expected_minutes
        count = fetch.call_count
        service.refresh_user_selected_rates(user_id=1)
        assert fetch.call_count == count
    service.repo.upsert_bank_rate.assert_not_called()
    service.db.commit.assert_not_called()
    assert "reason=network" in caplog.text
    assert "private error details" not in caplog.text


def test_empty_response_is_failure_and_success_resets_backoff(service, monkeypatch):
    monkeypatch.setattr(service, "_fetch_provider", lambda _: [])
    service.refresh_user_selected_rates(user_id=1)
    assert rates._PROVIDER_FAILURES["sber"] == 1
    quote = rates.BankCurrencyQuote(
        "sber", "Сбер", "EUR", 1, Decimal("3.4"), Decimal("3.5"), "cash", None,
        "https://example.test", None,
    )
    monkeypatch.setattr(service, "_fetch_provider", lambda _: [quote])
    monkeypatch.setattr(service, "_serialize", lambda row, **_: {"bank": row.bank_code})
    service.repo.upsert_bank_rate.return_value = SimpleNamespace(bank_code="sber")
    rates._LAST_PROVIDER_ATTEMPT["sber"] = datetime.now(timezone.utc) - timedelta(minutes=16)
    assert service.refresh_user_selected_rates(user_id=1) == [{"bank": "sber"}]
    assert "sber" not in rates._PROVIDER_FAILURES
    service.db.commit.assert_called_once()


def test_failure_classification_uses_exception_chain_not_error_text():
    exc = httpx.ConnectError("not logged")
    exc.__cause__ = socket.gaierror(-5, "not logged")
    assert rates._provider_error_category(exc) == "dns"
    assert rates._provider_error_category(httpx.ReadTimeout("timeout")) == "timeout"
    response = httpx.Response(410, request=httpx.Request("GET", "https://example.test"))
    assert rates._provider_error_category(httpx.HTTPStatusError("gone", request=response.request, response=response)) == "http_410"
