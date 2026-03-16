from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Any

import httpx

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.repositories.user_repo import UserRepository
from app.services.plan_reminder_service import PlanReminderService


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


def _format_user_label(user) -> str:
    identity = next((item for item in (user.identities or []) if item.provider == "telegram"), None)
    username = f"@{identity.username}" if identity and identity.username else "—"
    telegram_id = identity.provider_user_id if identity else "—"
    return (
        f"Имя: {user.display_name or 'Без имени'}\n"
        f"Username: {username}\n"
        f"Telegram ID: {telegram_id}\n"
        f"User ID: {user.id}"
    )


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


async def handle_callback_query(client: TelegramBotClient, query: dict[str, Any]) -> None:
    settings = get_settings()
    callback_id = str(query.get("id") or "")
    data = str(query.get("data") or "")
    from_user = query.get("from") or {}
    admin_telegram_id = str(from_user.get("id") or "")
    message = query.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    message_id = message.get("message_id")

    if admin_telegram_id not in settings.admin_telegram_id_set:
        await _answer_callback(client, callback_id, "Недостаточно прав")
        return

    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "access" or parts[1] not in {"approve", "reject"}:
        await _answer_callback(client, callback_id, "Неизвестное действие")
        return

    action = parts[1]
    try:
        user_id = int(parts[2])
    except ValueError:
        await _answer_callback(client, callback_id, "Некорректный пользователь")
        return

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        user = repo.get_by_id(user_id)
        if not user:
            await _answer_callback(client, callback_id, "Пользователь не найден")
            return
        next_status = "approved" if action == "approve" else "rejected"
        changed = user.status != next_status
        user.status = next_status
        db.commit()
        db.refresh(user)
        status_label = "Одобрен" if next_status == "approved" else "Отклонен"
        text = f"Заявка обработана: {status_label}\n\n{_format_user_label(user)}"
        if chat_id and message_id:
            await client.call(
                "editMessageText",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": text,
                },
            )
        await _answer_callback(client, callback_id, status_label if changed else f"Уже: {status_label.lower()}")
    finally:
        db.close()


async def process_plan_reminders(client: TelegramBotClient) -> None:
    db = SessionLocal()
    try:
        service = PlanReminderService(db)
        for payload in service.collect_due_reminders():
            try:
                await client.call(
                    "sendMessage",
                    {
                        "chat_id": payload["chat_id"],
                        "text": service.build_reminder_text(payload),
                        "disable_web_page_preview": True,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("telegram plan reminder failed for user %s: %s", payload["user_id"], exc)
                continue
            service.mark_reminded_items([*payload.get("overdue_items", []), *payload.get("due_items", [])])
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
    logger.info("telegram admin bot started")
    try:
        while True:
            now_mono = monotonic()
            if now_mono - last_plan_reminder_scan_at >= 60.0:
                try:
                    await process_plan_reminders(client)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("telegram plan reminder scan failed: %s", exc)
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
                logger.warning(
                    "telegram getUpdates read timeout after %ss, retrying",
                    settings.telegram_bot_poll_timeout_seconds,
                )
                continue
            except httpx.RequestError as exc:
                logger.warning("telegram getUpdates request failed, retrying: %s", exc)
                await asyncio.sleep(2)
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
