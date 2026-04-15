import asyncio
import logging

import httpx

from app.core.logging import SensitiveDataFilter
from app.core.logging import log_telegram_bot_event
from scripts.run_telegram_admin_bot import TelegramBotClient, TelegramBotHTTPError


def test_log_telegram_bot_event_writes_structured_fields(caplog):
    with caplog.at_level("INFO", logger="financial_assistant_admin_bot"):
        log_telegram_bot_event("callback_processed", admin_telegram_id="42", action="approve", user_id=7)

    messages = [record.getMessage() for record in caplog.records if record.name == "financial_assistant_admin_bot"]
    assert any("telegram_bot_event event=callback_processed" in message for message in messages)
    assert any("admin_telegram_id=42" in message for message in messages)
    assert any("action=approve" in message for message in messages)
    assert any("user_id=7" in message for message in messages)


def test_sensitive_data_filter_redacts_telegram_bot_tokens(monkeypatch):
    token = "123456789:AAExampleSecretToken_123"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="failed url=https://api.telegram.org/bot%s/getUpdates",
        args=(token,),
        exc_info=None,
    )

    assert SensitiveDataFilter().filter(record)

    message = record.getMessage()
    assert token not in message
    assert "bot<telegram-token-redacted>" in message


def test_telegram_bot_client_hides_http_status_error_url():
    token = "123456789:AAExampleSecretToken_123"
    client = TelegramBotClient(token=token, timeout_seconds=25)

    class _FakeHttp:
        async def post(self, url, json):  # noqa: ANN001
            request = httpx.Request("POST", url)
            return httpx.Response(409, request=request)

        async def aclose(self):
            return None

    client.http = _FakeHttp()

    async def _call():
        try:
            await client.call("getUpdates")
        finally:
            await client.close()

    try:
        asyncio.run(_call())
    except TelegramBotHTTPError as exc:
        message = str(exc)
    else:
        raise AssertionError("TelegramBotHTTPError was not raised")

    assert "409" in message
    assert "getUpdates" in message
    assert token not in message
    assert "api.telegram.org" not in message
