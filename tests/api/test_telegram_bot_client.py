from __future__ import annotations

import asyncio
from contextlib import contextmanager

import httpx
import pytest

from app.services.telegram_currency_digest_bot_service import TelegramCurrencyDigestDelivery
import scripts.run_telegram_admin_bot as telegram_bot
from scripts.run_telegram_admin_bot import (
    TelegramBotClient,
    TelegramBotHTTPError,
    TelegramBotRequestError,
    process_currency_digests,
    send_currency_digest_delivery,
)


PNG_BYTES = b"\x89PNG\r\n\x1a\nfinancial-assistant-test"


@contextmanager
def _always_acquired(*args, **kwargs):  # noqa: ANN002, ANN003
    yield True


def test_send_photo_posts_png_as_multipart_form_data():
    captured_requests: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 17}})

    async def _send() -> dict:
        client = TelegramBotClient(token="test-token", timeout_seconds=25)
        await client.close()
        client.http = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
        try:
            return await client.send_photo(
                chat_id=42,
                png_bytes=PNG_BYTES,
                caption="Курсы за 7 дней",
            )
        finally:
            await client.close()

    result = asyncio.run(_send())

    assert result["result"]["message_id"] == 17
    assert len(captured_requests) == 1
    request = captured_requests[0]
    assert request.url.path.endswith("/sendPhoto")
    assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
    assert b'name="chat_id"' in request.content
    assert b"\r\n\r\n42\r\n" in request.content
    assert b'name="caption"' in request.content
    assert "Курсы за 7 дней".encode() in request.content
    assert b'name="photo"; filename="currency-digest.png"' in request.content
    assert b"Content-Type: image/png" in request.content
    assert PNG_BYTES in request.content


def test_send_photo_maps_http_status_without_leaking_token():
    token = "123456789:AAExampleSecretToken_123"

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(413, request=request)

    async def _send() -> None:
        client = TelegramBotClient(token=token, timeout_seconds=25)
        await client.close()
        client.http = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
        try:
            await client.send_photo(chat_id="42", png_bytes=PNG_BYTES, caption="Digest")
        finally:
            await client.close()

    with pytest.raises(TelegramBotHTTPError) as exc_info:
        asyncio.run(_send())

    assert exc_info.value.method == "sendPhoto"
    assert exc_info.value.status_code == 413
    assert token not in str(exc_info.value)
    assert "api.telegram.org" not in str(exc_info.value)


def test_send_photo_maps_transport_errors_without_leaking_token():
    token = "123456789:AAExampleSecretToken_123"

    def _handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    async def _send() -> None:
        client = TelegramBotClient(token=token, timeout_seconds=25)
        await client.close()
        client.http = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
        try:
            await client.send_photo(chat_id="42", png_bytes=PNG_BYTES, caption="Digest")
        finally:
            await client.close()

    with pytest.raises(TelegramBotRequestError) as exc_info:
        asyncio.run(_send())

    assert exc_info.value.method == "sendPhoto"
    assert exc_info.value.error_type == "ConnectError"
    assert token not in str(exc_info.value)
    assert "api.telegram.org" not in str(exc_info.value)


def test_send_photo_preserves_read_timeout_for_existing_retry_handling():
    def _handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out", request=request)

    async def _send() -> None:
        client = TelegramBotClient(token="test-token", timeout_seconds=25)
        await client.close()
        client.http = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
        try:
            await client.send_photo(chat_id="42", png_bytes=PNG_BYTES, caption="Digest")
        finally:
            await client.close()

    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(_send())


def test_send_photo_rejects_empty_png_before_request():
    client = TelegramBotClient(token="test-token", timeout_seconds=25)

    async def _send() -> None:
        try:
            await client.send_photo(chat_id=42, png_bytes=b"", caption="Digest")
        finally:
            await client.close()

    with pytest.raises(ValueError, match="png_bytes must not be empty"):
        asyncio.run(_send())


def _digest_delivery(*, with_photo: bool = True) -> TelegramCurrencyDigestDelivery:
    return TelegramCurrencyDigestDelivery(
        chat_id="42",
        text="Полный валютный дайджест",
        user_id=7,
        tracked_currencies=["USD", "EUR"],
        photo_png=PNG_BYTES if with_photo else None,
        photo_caption="Краткий валютный дайджест" if with_photo else None,
    )


def test_currency_digest_delivery_sends_one_photo_message_with_caption():
    class _Client:
        def __init__(self):
            self.photo_calls = []
            self.message_calls = []

        async def send_photo(self, **kwargs):  # noqa: ANN003
            self.photo_calls.append(kwargs)

        async def call(self, method, payload):  # noqa: ANN001
            self.message_calls.append((method, payload))

    client = _Client()
    delivery_format = asyncio.run(send_currency_digest_delivery(client, _digest_delivery()))

    assert delivery_format == "photo"
    assert client.photo_calls == [
        {
            "chat_id": "42",
            "png_bytes": PNG_BYTES,
            "caption": "Краткий валютный дайджест",
        }
    ]
    assert client.message_calls == []


def test_currency_digest_delivery_falls_back_to_text_when_photo_send_fails():
    class _Client:
        def __init__(self):
            self.message_calls = []

        async def send_photo(self, **kwargs):  # noqa: ANN003
            raise RuntimeError("Telegram rejected photo")

        async def call(self, method, payload):  # noqa: ANN001
            self.message_calls.append((method, payload))

    client = _Client()
    delivery_format = asyncio.run(send_currency_digest_delivery(client, _digest_delivery()))

    assert delivery_format == "text"
    assert client.message_calls == [
        (
            "sendMessage",
            {
                "chat_id": "42",
                "text": "Полный валютный дайджест",
                "disable_web_page_preview": True,
            },
        )
    ]


def test_currency_digest_delivery_does_not_send_duplicate_text_after_ambiguous_timeout():
    class _Client:
        def __init__(self):
            self.message_calls = []

        async def send_photo(self, **kwargs):  # noqa: ANN003
            request = httpx.Request("POST", "https://api.telegram.org/sendPhoto")
            raise httpx.ReadTimeout("response timed out", request=request)

        async def call(self, method, payload):  # noqa: ANN001
            self.message_calls.append((method, payload))

    client = _Client()
    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(send_currency_digest_delivery(client, _digest_delivery()))

    assert client.message_calls == []


def test_currency_digest_delivery_keeps_existing_text_only_mode():
    class _Client:
        def __init__(self):
            self.photo_calls = []
            self.message_calls = []

        async def send_photo(self, **kwargs):  # noqa: ANN003
            self.photo_calls.append(kwargs)

        async def call(self, method, payload):  # noqa: ANN001
            self.message_calls.append((method, payload))

    client = _Client()
    delivery_format = asyncio.run(
        send_currency_digest_delivery(client, _digest_delivery(with_photo=False))
    )

    assert delivery_format == "text"
    assert client.photo_calls == []
    assert client.message_calls[0][0] == "sendMessage"


def test_currency_digest_process_marks_successful_photo_delivery(monkeypatch):
    delivery = _digest_delivery()

    class _Db:
        closed = False

        def close(self):
            self.closed = True

    class _Service:
        def __init__(self):
            self.marked = []
            self.released = []

        def list_due_deliveries(self):
            return [delivery]

        def claim_delivery(self, candidate):  # noqa: ANN001
            return candidate is delivery

        def mark_delivery_sent(self, candidate, *, delivery_format):  # noqa: ANN001
            self.marked.append((candidate, delivery_format))

        def release_delivery(self, candidate):  # noqa: ANN001
            self.released.append(candidate)

    class _Client:
        async def send_photo(self, **kwargs):  # noqa: ANN003
            return {"ok": True}

        async def call(self, method, payload):  # noqa: ANN001
            raise AssertionError((method, payload))

    db = _Db()
    service = _Service()
    monkeypatch.setattr(telegram_bot, "SessionLocal", lambda: db)
    monkeypatch.setattr(telegram_bot, "TelegramCurrencyDigestBotService", lambda _db: service)
    monkeypatch.setattr(telegram_bot, "try_background_job_lock", _always_acquired)

    asyncio.run(process_currency_digests(_Client()))

    assert service.marked == [(delivery, "photo")]
    assert service.released == []
    assert db.closed is True


def test_currency_digest_process_releases_claim_when_photo_and_text_both_fail(monkeypatch):
    delivery = _digest_delivery()

    class _Db:
        closed = False

        def close(self):
            self.closed = True

    class _Service:
        def __init__(self):
            self.marked = []
            self.released = []

        def list_due_deliveries(self):
            return [delivery]

        def claim_delivery(self, candidate):  # noqa: ANN001
            return candidate is delivery

        def mark_delivery_sent(self, candidate, *, delivery_format):  # noqa: ANN001
            self.marked.append((candidate, delivery_format))

        def release_delivery(self, candidate):  # noqa: ANN001
            self.released.append(candidate)

    class _Client:
        async def send_photo(self, **kwargs):  # noqa: ANN003
            raise RuntimeError("photo rejected")

        async def call(self, method, payload):  # noqa: ANN001
            raise RuntimeError("text rejected")

    db = _Db()
    service = _Service()
    monkeypatch.setattr(telegram_bot, "SessionLocal", lambda: db)
    monkeypatch.setattr(telegram_bot, "TelegramCurrencyDigestBotService", lambda _db: service)
    monkeypatch.setattr(telegram_bot, "try_background_job_lock", _always_acquired)

    asyncio.run(process_currency_digests(_Client()))

    assert service.marked == []
    assert service.released == [delivery]
    assert db.closed is True
