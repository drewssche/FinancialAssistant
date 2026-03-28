from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import log_telegram_bot_event
from app.db.session import SessionLocal
from app.services.telegram_admin_bot_service import (
    TelegramAdminBotService,
    TelegramAdminTargetUserNotFoundError,
)
from app.services.telegram_debt_reminder_bot_service import TelegramDebtReminderBotService
from app.services.telegram_currency_digest_bot_service import TelegramCurrencyDigestBotService
from app.services.telegram_currency_alert_bot_service import TelegramCurrencyAlertBotService
from app.services.telegram_plan_bot_service import (
    TelegramPlanAlreadyCompletedError,
    TelegramPlanBotService,
    TelegramPlanNotFoundError,
    TelegramPlanUserNotFoundError,
)
from app.services.telegram_plan_reminder_bot_service import TelegramPlanReminderBotService
from app.services.currency_rate_refresh_service import CurrencyRateRefreshService


logger = logging.getLogger("financial_assistant_admin_bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


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

    async def call(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self.http.post(f"{self.base_url}/{method}", json=payload or {})
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error for {method}: {data}")
        return data


async def _answer_callback(client: TelegramBotClient, callback_query_id: str, text: str) -> None:
    await client.call(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": False,
        },
    )


async def handle_message(client: TelegramBotClient, message: dict[str, Any]) -> None:
    settings = get_settings()
    text = str(message.get("text") or "").strip().split(maxsplit=1)[0]
    chat_id = (message.get("chat") or {}).get("id")
    if text != "/start" or not chat_id:
        return
    is_admin = str(chat_id) in settings.admin_telegram_id_set
    reply = (
        "Уведомления о новых заявках включены."
        if is_admin
        else "Бот используется для уведомлений админов о новых заявках."
    )
    await client.call("sendMessage", {"chat_id": chat_id, "text": reply})
    log_telegram_bot_event("start_message_sent", chat_id=chat_id, is_admin=is_admin)


async def handle_callback_query(client: TelegramBotClient, query: dict[str, Any]) -> None:
    settings = get_settings()
    callback_id = str(query.get("id") or "")
    data = str(query.get("data") or "")
    from_user = query.get("from") or {}
    actor_telegram_id = str(from_user.get("id") or "")
    message = query.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    message_id = message.get("message_id")

    access_parts = data.split(":")
    if len(access_parts) == 3 and access_parts[0] == "access":
        if actor_telegram_id not in settings.admin_telegram_id_set:
            await _answer_callback(client, callback_id, "Недостаточно прав")
            log_telegram_bot_event("callback_denied", admin_telegram_id=actor_telegram_id or "unknown", data=data or "empty")
            return
        if access_parts[1] not in {"approve", "reject"}:
            await _answer_callback(client, callback_id, "Неизвестное действие")
            log_telegram_bot_event("callback_invalid", admin_telegram_id=actor_telegram_id, data=data or "empty")
            return
        action = access_parts[1]
        try:
            user_id = int(access_parts[2])
        except ValueError:
            await _answer_callback(client, callback_id, "Некорректный пользователь")
            log_telegram_bot_event("callback_invalid_user_id", admin_telegram_id=actor_telegram_id, raw_user_id=access_parts[2])
            return

        db = SessionLocal()
        try:
            try:
                result = TelegramAdminBotService(db).review_access_request(action=action, user_id=user_id)
            except TelegramAdminTargetUserNotFoundError as exc:
                await _answer_callback(client, callback_id, str(exc))
                log_telegram_bot_event(
                    "callback_user_not_found",
                    admin_telegram_id=actor_telegram_id,
                    action=action,
                    user_id=user_id,
                )
                return
            if chat_id and message_id:
                await client.call(
                    "editMessageText",
                    {
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "text": result.message_text,
                    },
                )
            await _answer_callback(client, callback_id, result.callback_text)
            log_telegram_bot_event(
                "callback_processed",
                admin_telegram_id=actor_telegram_id,
                action=action,
                user_id=user_id,
                callback_text=result.callback_text,
            )
        finally:
            db.close()
        return

    confirm_parts = data.split(":", 1)
    if len(confirm_parts) != 2 or confirm_parts[0] != "planc":
        await _answer_callback(client, callback_id, "Неизвестное действие")
        log_telegram_bot_event("callback_invalid", actor_telegram_id=actor_telegram_id or "unknown", data=data or "empty")
        return

    try:
        plan_id = int(confirm_parts[1])
    except ValueError:
        await _answer_callback(client, callback_id, "Некорректный план")
        log_telegram_bot_event("plan_confirm_invalid_plan_id", telegram_id=actor_telegram_id or "unknown", raw_plan_id=confirm_parts[1])
        return

    db = SessionLocal()
    try:
        try:
            result = TelegramPlanBotService(db).confirm_plan_from_telegram(
                telegram_id=actor_telegram_id,
                plan_id=plan_id,
            )
        except TelegramPlanUserNotFoundError as exc:
            await _answer_callback(client, callback_id, str(exc))
            log_telegram_bot_event(
                "plan_confirm_user_not_found",
                telegram_id=actor_telegram_id or "unknown",
                plan_id=plan_id,
            )
            return
        except TelegramPlanNotFoundError as exc:
            await _answer_callback(client, callback_id, str(exc))
            log_telegram_bot_event(
                "plan_confirm_plan_not_found",
                telegram_id=actor_telegram_id or "unknown",
                plan_id=plan_id,
            )
            return
        except TelegramPlanAlreadyCompletedError as exc:
            await _answer_callback(client, callback_id, str(exc))
            log_telegram_bot_event(
                "plan_confirm_already_completed",
                telegram_id=actor_telegram_id or "unknown",
                plan_id=plan_id,
            )
            return
        if chat_id and message_id:
            await client.call(
                "editMessageText",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": result.message_text,
                },
            )
        await _answer_callback(client, callback_id, result.callback_text)
        log_telegram_bot_event(
            "plan_confirm_processed",
            telegram_id=actor_telegram_id or "unknown",
            plan_id=plan_id,
            callback_text=result.callback_text,
        )
    finally:
        db.close()


async def process_plan_reminders(client: TelegramBotClient) -> None:
    db = SessionLocal()
    try:
        service = TelegramPlanReminderBotService(db)
        for delivery in service.list_due_deliveries():
            try:
                await client.call(
                    "sendMessage",
                    {
                        "chat_id": delivery.chat_id,
                        "text": delivery.text,
                        "reply_markup": delivery.reply_markup,
                        "disable_web_page_preview": True,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                log_telegram_bot_event(
                    "plan_reminder_failed",
                    user_id=delivery.user_id,
                    plan_id=delivery.plan_id,
                    error=type(exc).__name__,
                )
                logger.warning(
                    "telegram plan reminder failed for user %s plan %s: %s",
                    delivery.user_id,
                    delivery.plan_id,
                    exc,
                )
                continue
            service.mark_delivery_sent(delivery)
            log_telegram_bot_event(
                "plan_reminder_sent",
                chat_id=delivery.chat_id,
                user_id=delivery.user_id,
                plan_id=delivery.plan_id,
            )
    finally:
        db.close()


async def process_debt_reminders(client: TelegramBotClient) -> None:
    db = SessionLocal()
    try:
        service = TelegramDebtReminderBotService(db)
        for delivery in service.list_due_deliveries():
            try:
                await client.call(
                    "sendMessage",
                    {
                        "chat_id": delivery.chat_id,
                        "text": delivery.text,
                        "disable_web_page_preview": True,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                log_telegram_bot_event(
                    "debt_reminder_failed",
                    user_id=delivery.user_id,
                    debt_id=delivery.debt_id,
                    error=type(exc).__name__,
                )
                logger.warning(
                    "telegram debt reminder failed for user %s debt %s: %s",
                    delivery.user_id,
                    delivery.debt_id,
                    exc,
                )
                continue
            service.mark_delivery_sent(delivery)
            log_telegram_bot_event(
                "debt_reminder_sent",
                chat_id=delivery.chat_id,
                user_id=delivery.user_id,
                debt_id=delivery.debt_id,
            )
    finally:
        db.close()


async def process_currency_refresh() -> None:
    db = SessionLocal()
    try:
        CurrencyRateRefreshService(db).refresh_due_tracked_rates()
    finally:
        db.close()


async def process_currency_digests(client: TelegramBotClient) -> None:
    db = SessionLocal()
    try:
        service = TelegramCurrencyDigestBotService(db)
        for delivery in service.list_due_deliveries():
            try:
                await client.call(
                    "sendMessage",
                    {
                        "chat_id": delivery.chat_id,
                        "text": delivery.text,
                        "disable_web_page_preview": True,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                log_telegram_bot_event(
                    "currency_digest_failed",
                    user_id=delivery.user_id,
                    error=type(exc).__name__,
                )
                logger.warning(
                    "telegram currency digest failed for user %s: %s",
                    delivery.user_id,
                    exc,
                )
                continue
            service.mark_delivery_sent(delivery)
            log_telegram_bot_event(
                "currency_digest_sent",
                chat_id=delivery.chat_id,
                user_id=delivery.user_id,
                tracked_count=len(delivery.tracked_currencies),
            )
    finally:
        db.close()


async def process_currency_alerts(client: TelegramBotClient) -> None:
    db = SessionLocal()
    try:
        service = TelegramCurrencyAlertBotService(db)
        for delivery in service.list_due_deliveries():
            try:
                await client.call(
                    "sendMessage",
                    {
                        "chat_id": delivery.chat_id,
                        "text": delivery.text,
                        "disable_web_page_preview": True,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                log_telegram_bot_event(
                    "currency_alert_failed",
                    user_id=delivery.user_id,
                    error=type(exc).__name__,
                )
                logger.warning(
                    "telegram currency alert failed for user %s: %s",
                    delivery.user_id,
                    exc,
                )
                continue
            service.mark_delivery_sent(delivery)
            log_telegram_bot_event(
                "currency_alert_sent",
                chat_id=delivery.chat_id,
                user_id=delivery.user_id,
                trigger_count=len(delivery.triggers),
            )
    finally:
        db.close()


async def run() -> None:
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    if not token or token == "change_me":
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    client = TelegramBotClient(token=token, timeout_seconds=settings.telegram_bot_poll_timeout_seconds)
    offset = 0
    last_plan_reminder_scan_at = 0.0
    reminder_scan_interval_seconds = max(15, int(settings.telegram_plan_reminder_scan_interval_seconds))
    retry_delay_seconds = max(1, int(settings.telegram_bot_retry_delay_seconds))
    logger.info("telegram admin bot started")
    log_telegram_bot_event(
        "bot_started",
        poll_timeout_seconds=settings.telegram_bot_poll_timeout_seconds,
        reminder_scan_interval_seconds=reminder_scan_interval_seconds,
    )
    try:
        while True:
            now_mono = monotonic()
            if now_mono - last_plan_reminder_scan_at >= reminder_scan_interval_seconds:
                try:
                    await process_plan_reminders(client)
                except Exception as exc:  # noqa: BLE001
                    log_telegram_bot_event("plan_reminder_scan_failed", error=type(exc).__name__)
                    logger.warning("telegram plan reminder scan failed: %s", exc)
                try:
                    await process_debt_reminders(client)
                except Exception as exc:  # noqa: BLE001
                    log_telegram_bot_event("debt_reminder_scan_failed", error=type(exc).__name__)
                    logger.warning("telegram debt reminder scan failed: %s", exc)
                try:
                    await process_currency_refresh()
                except Exception as exc:  # noqa: BLE001
                    log_telegram_bot_event("currency_refresh_scan_failed", error=type(exc).__name__)
                    logger.warning("currency rate refresh scan failed: %s", exc)
                try:
                    await process_currency_digests(client)
                except Exception as exc:  # noqa: BLE001
                    log_telegram_bot_event("currency_digest_scan_failed", error=type(exc).__name__)
                    logger.warning("telegram currency digest scan failed: %s", exc)
                try:
                    await process_currency_alerts(client)
                except Exception as exc:  # noqa: BLE001
                    log_telegram_bot_event("currency_alert_scan_failed", error=type(exc).__name__)
                    logger.warning("telegram currency alert scan failed: %s", exc)
                last_plan_reminder_scan_at = now_mono
            try:
                data = await client.call(
                    "getUpdates",
                    {
                        "offset": offset,
                        "timeout": settings.telegram_bot_poll_timeout_seconds,
                        "allowed_updates": ["message", "callback_query"],
                    },
                )
            except httpx.ReadTimeout:
                log_telegram_bot_event(
                    "get_updates_read_timeout",
                    timeout_seconds=settings.telegram_bot_poll_timeout_seconds,
                )
                logger.warning(
                    "telegram getUpdates read timeout after %ss, retrying",
                    settings.telegram_bot_poll_timeout_seconds,
                )
                continue
            except httpx.RequestError as exc:
                log_telegram_bot_event("get_updates_request_failed", error=type(exc).__name__)
                logger.warning("telegram getUpdates request failed, retrying: %s", exc)
                await asyncio.sleep(retry_delay_seconds)
                continue
            for item in data.get("result", []):
                offset = max(offset, int(item["update_id"]) + 1)
                if item.get("message"):
                    await handle_message(client, item["message"])
                if item.get("callback_query"):
                    await handle_callback_query(client, item["callback_query"])
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(run())
