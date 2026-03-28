from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.core.logging import log_telegram_debt_event

logger = logging.getLogger(__name__)


def _build_debt_repaid_text(
    *,
    counterparty: str,
    direction: str,
    amount: Decimal,
    currency: str,
    repayment_date: date,
    note: str | None,
) -> str:
    direction_label = "Вы вернули долг" if direction == "borrow" else "Вам вернули долг"
    note_block = f"\nКомментарий: {note}" if note else ""
    return (
        "Долг погашен\n\n"
        f"{direction_label}\n"
        f"Контрагент: {counterparty}\n"
        f"Сумма погашения: {amount:.2f} {currency}\n"
        f"Дата: {repayment_date.isoformat()}"
        f"{note_block}"
    )


def notify_debt_repaid_owner(
    *,
    owner_telegram_id: str,
    debt_id: int,
    counterparty: str,
    direction: str,
    amount: Decimal,
    currency: str = "BYN",
    repayment_date: date,
    note: str | None = None,
) -> None:
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    if not token or token == "change_me" or not owner_telegram_id.strip():
        return

    text = _build_debt_repaid_text(
        counterparty=counterparty,
        direction=direction,
        amount=amount,
        currency=currency,
        repayment_date=repayment_date,
        note=note,
    )
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    log_telegram_debt_event(
        "debt_repaid_notification_attempted",
        debt_id=debt_id,
        owner_telegram_id=owner_telegram_id,
        direction=direction,
    )
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.post(
                url,
                json={
                    "chat_id": owner_telegram_id,
                    "text": text,
                    "disable_web_page_preview": True,
                },
            )
            response.raise_for_status()
        log_telegram_debt_event(
            "debt_repaid_notification_sent",
            debt_id=debt_id,
            owner_telegram_id=owner_telegram_id,
            direction=direction,
        )
    except Exception as exc:  # noqa: BLE001
        log_telegram_debt_event(
            "debt_repaid_notification_failed",
            debt_id=debt_id,
            owner_telegram_id=owner_telegram_id,
            direction=direction,
            error=type(exc).__name__,
        )
        logger.warning("telegram debt notification failed for %s: %s", owner_telegram_id, exc)
