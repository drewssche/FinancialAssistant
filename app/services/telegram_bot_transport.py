from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.logging import log_telegram_bot_event
from app.services.telegram_currency_digest_bot_service import TelegramCurrencyDigestDelivery


logger = logging.getLogger("financial_assistant_admin_bot")


class TelegramBotHTTPError(RuntimeError):
    def __init__(self, method: str, status_code: int) -> None:
        self.method = method
        self.status_code = status_code
        super().__init__(f"Telegram API HTTP error for {method}: status_code={status_code}")


class TelegramBotRequestError(RuntimeError):
    def __init__(self, method: str, error_type: str) -> None:
        self.method = method
        self.error_type = error_type
        super().__init__(f"Telegram API request failed for {method}: error={error_type}")


class TelegramBotClient:
    def __init__(self, token: str, timeout_seconds: int) -> None:
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.timeout_seconds = max(10, int(timeout_seconds))
        # Long polling keeps the connection open on Telegram's side, so the read timeout
        # needs a larger cushion than connect/write operations.
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                write=10.0,
                pool=10.0,
                read=self.timeout_seconds + 15.0,
            )
        )

    async def close(self) -> None:
        await self.http.aclose()

    async def _post(self, method: str, **request_kwargs: Any) -> dict[str, Any]:
        try:
            response = await self.http.post(f"{self.base_url}/{method}", **request_kwargs)
        except httpx.ReadTimeout:
            raise
        except httpx.RequestError as exc:
            raise TelegramBotRequestError(method, type(exc).__name__) from None
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TelegramBotHTTPError(method, exc.response.status_code) from None
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error for {method}: {data}")
        return data

    async def call(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._post(method, json=payload or {})

    async def send_photo(
        self,
        *,
        chat_id: int | str,
        png_bytes: bytes,
        caption: str,
    ) -> dict[str, Any]:
        if not png_bytes:
            raise ValueError("png_bytes must not be empty")
        return await self._post(
            "sendPhoto",
            data={"chat_id": str(chat_id), "caption": caption},
            files={"photo": ("currency-digest.png", png_bytes, "image/png")},
        )


async def send_currency_digest_delivery(
    client: TelegramBotClient,
    delivery: TelegramCurrencyDigestDelivery,
) -> str:
    if delivery.photo_png:
        try:
            await client.send_photo(
                chat_id=delivery.chat_id,
                png_bytes=delivery.photo_png,
                caption=delivery.photo_caption or delivery.text[:1024],
            )
            return "photo"
        except httpx.ReadTimeout:
            # Telegram may already have accepted the upload before the response timed out.
            # Do not create a guaranteed photo + text duplicate for an ambiguous outcome.
            raise
        except TelegramBotRequestError as exc:
            if exc.error_type not in {"ConnectError", "ConnectTimeout", "PoolTimeout"}:
                raise
            log_telegram_bot_event(
                "currency_digest_photo_failed",
                user_id=delivery.user_id,
                error=exc.error_type,
            )
            logger.warning(
                "telegram currency digest photo connection failed for user %s, "
                "falling back to text: %s",
                delivery.user_id,
                exc.error_type,
            )
        except Exception as exc:  # noqa: BLE001 - definite photo rejection keeps text available.
            log_telegram_bot_event(
                "currency_digest_photo_failed",
                user_id=delivery.user_id,
                error=type(exc).__name__,
            )
            logger.warning(
                "telegram currency digest photo failed for user %s, falling back to text: %s",
                delivery.user_id,
                type(exc).__name__,
            )
    await client.call(
        "sendMessage",
        {
            "chat_id": delivery.chat_id,
            "text": delivery.text,
            "disable_web_page_preview": True,
        },
    )
    return "text"


async def _send_currency_digest_with_client(
    *,
    token: str,
    timeout_seconds: int,
    delivery: TelegramCurrencyDigestDelivery,
) -> str:
    client = TelegramBotClient(token=token, timeout_seconds=timeout_seconds)
    try:
        return await send_currency_digest_delivery(client, delivery)
    finally:
        await client.close()


def send_currency_digest_delivery_sync(
    *,
    token: str,
    timeout_seconds: int,
    delivery: TelegramCurrencyDigestDelivery,
) -> str:
    """Send a digest from a synchronous FastAPI worker and confirm acceptance."""
    return asyncio.run(
        _send_currency_digest_with_client(
            token=token,
            timeout_seconds=timeout_seconds,
            delivery=delivery,
        )
    )
