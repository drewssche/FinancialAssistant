from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import log_admin_notification_event
from app.db.models import AuthIdentity, UserPreference
from app.services.telegram_message_format import ICON_ACCESS, title

logger = logging.getLogger(__name__)


def _build_request_text(
    *,
    user_id: int,
    display_name: str | None,
    username: str | None,
    telegram_id: str,
    created_at: datetime | None,
    timezone_name: str = "Europe/Minsk",
) -> str:
    name = (display_name or "Без имени").strip()
    handle = f"@{username}" if username else "—"
    try:
        local_zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        local_zone = ZoneInfo("Europe/Minsk")
    if created_at:
        instant = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        local = instant.astimezone(local_zone)
        offset = local.strftime("%z")
        created_label = f"{local:%d.%m.%Y %H:%M} (UTC{offset[:3]}:{offset[3:]})"
    else:
        created_label = "—"
    return (
        f"{title(ICON_ACCESS, 'Новая заявка на доступ')}\n\n"
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
    db: Session | None = None,
) -> None:
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    admin_ids = settings.admin_telegram_id_set
    if not token or token == "change_me" or not admin_ids:
        return

    admin_timezones: dict[str, str] = {}
    if db is not None:
        query = (
            select(AuthIdentity, UserPreference)
            .outerjoin(UserPreference, UserPreference.user_id == AuthIdentity.user_id)
            .where(AuthIdentity.provider == "telegram", AuthIdentity.provider_user_id.in_(admin_ids))
        )
        for identity, preferences in db.execute(query):
            prefs = preferences.data if preferences and isinstance(preferences.data, dict) else {}
            ui = prefs.get("ui") if isinstance(prefs.get("ui"), dict) else {}
            name = str(ui.get("timezone") or "auto").strip()
            if not name or name == "auto":
                name = str(ui.get("browser_timezone") or "").strip()
            admin_timezones[identity.provider_user_id] = name or "Europe/Minsk"
    payload = {
        "reply_markup": _build_reply_markup(user_id),
        "disable_web_page_preview": True,
    }
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    with httpx.Client(timeout=3.0) as client:
        for admin_id in admin_ids:
            text = _build_request_text(
                user_id=user_id,
                display_name=display_name,
                username=username,
                telegram_id=telegram_id,
                created_at=created_at,
                timezone_name=admin_timezones.get(admin_id, "Europe/Minsk"),
            )
            log_admin_notification_event(
                "admin_notification_attempted",
                user_id=user_id,
                telegram_id=telegram_id,
                admin_telegram_id=admin_id,
                has_username=bool(username),
            )
            try:
                response = client.post(url, json={**payload, "text": text, "chat_id": admin_id})
                response.raise_for_status()
                log_admin_notification_event(
                    "admin_notification_sent",
                    user_id=user_id,
                    telegram_id=telegram_id,
                    admin_telegram_id=admin_id,
                    has_username=bool(username),
                )
            except Exception as exc:  # noqa: BLE001
                log_admin_notification_event(
                    "admin_notification_failed",
                    user_id=user_id,
                    telegram_id=telegram_id,
                    admin_telegram_id=admin_id,
                    has_username=bool(username),
                    error=type(exc).__name__,
                )
                logger.warning("telegram admin notification failed for %s: %s", admin_id, exc)


def notify_redis_fallback_advisory(
    *,
    text: str,
    local_cache_entries: int,
    local_fallback_reads: int,
    local_fallback_writes: int,
    dashboard_summary_p95_ms: float,
) -> None:
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    admin_ids = settings.admin_telegram_id_set
    if not token or token == "change_me" or not admin_ids:
        return

    payload = {
        "text": text,
        "disable_web_page_preview": True,
    }
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    with httpx.Client(timeout=3.0) as client:
        for admin_id in admin_ids:
            log_admin_notification_event(
                "redis_fallback_advisory_attempted",
                admin_telegram_id=admin_id,
                local_cache_entries=local_cache_entries,
                local_fallback_reads=local_fallback_reads,
                local_fallback_writes=local_fallback_writes,
                dashboard_summary_p95_ms=round(max(dashboard_summary_p95_ms, 0.0), 3),
            )
            try:
                response = client.post(url, json={**payload, "chat_id": admin_id})
                response.raise_for_status()
                log_admin_notification_event(
                    "redis_fallback_advisory_sent",
                    admin_telegram_id=admin_id,
                    local_cache_entries=local_cache_entries,
                    local_fallback_reads=local_fallback_reads,
                    local_fallback_writes=local_fallback_writes,
                    dashboard_summary_p95_ms=round(max(dashboard_summary_p95_ms, 0.0), 3),
                )
            except Exception as exc:  # noqa: BLE001
                log_admin_notification_event(
                    "redis_fallback_advisory_failed",
                    admin_telegram_id=admin_id,
                    local_cache_entries=local_cache_entries,
                    local_fallback_reads=local_fallback_reads,
                    local_fallback_writes=local_fallback_writes,
                    dashboard_summary_p95_ms=round(max(dashboard_summary_p95_ms, 0.0), 3),
                    error=type(exc).__name__,
                )
                logger.warning("telegram redis fallback advisory failed for %s: %s", admin_id, exc)
