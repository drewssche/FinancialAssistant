from __future__ import annotations

import logging
from datetime import datetime

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _build_request_text(
    *,
    user_id: int,
    display_name: str | None,
    username: str | None,
    telegram_id: str,
    created_at: datetime | None,
) -> str:
    name = (display_name or "Без имени").strip()
    handle = f"@{username}" if username else "—"
    created_label = created_at.strftime("%d.%m.%Y %H:%M") if created_at else "—"
    return (
        "Новая заявка на доступ\n\n"
        f"Имя: {name}\n"
        f"Username: {handle}\n"
        f"Telegram ID: {telegram_id}\n"
        f"User ID: {user_id}\n"
        f"Создан: {created_label}"
    )


def _build_reply_markup(user_id: int) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "Approve", "callback_data": f"access:approve:{user_id}"},
                {"text": "Reject", "callback_data": f"access:reject:{user_id}"},
            ]
        ]
    }


def notify_new_pending_user(
    *,
    user_id: int,
    display_name: str | None,
    username: str | None,
    telegram_id: str,
    created_at: datetime | None,
) -> None:
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    admin_ids = settings.admin_telegram_id_set
    if not token or token == "change_me" or not admin_ids:
        return

    text = _build_request_text(
        user_id=user_id,
        display_name=display_name,
        username=username,
        telegram_id=telegram_id,
        created_at=created_at,
    )
    payload = {
        "text": text,
        "reply_markup": _build_reply_markup(user_id),
        "disable_web_page_preview": True,
    }
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    with httpx.Client(timeout=3.0) as client:
        for admin_id in admin_ids:
            try:
                response = client.post(url, json={**payload, "chat_id": admin_id})
                response.raise_for_status()
            except Exception as exc:  # noqa: BLE001
                logger.warning("telegram admin notification failed for %s: %s", admin_id, exc)
