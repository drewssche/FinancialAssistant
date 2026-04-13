from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.logging import log_background_job_event
from app.repositories.currency_repo import CurrencyRepository
from app.repositories.preference_repo import PreferenceRepository
from app.services.currency_rate_refresh_service import CurrencyRateRefreshService
from app.services.currency_service import CurrencyService
from app.services.telegram_message_format import ICON_CURRENCY, signed_decimal, title, trend_icon


@dataclass(frozen=True)
class TelegramCurrencyDigestDelivery:
    chat_id: str
    text: str
    user_id: int
    tracked_currencies: list[str]


class TelegramCurrencyDigestBotService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CurrencyRepository(db)
        self.preferences = PreferenceRepository(db)
        self.currency_service = CurrencyService(db)
        self.refresh_service = CurrencyRateRefreshService(db)

    def list_due_deliveries(self) -> list[TelegramCurrencyDigestDelivery]:
        deliveries: list[TelegramCurrencyDigestDelivery] = []
        for identity, preference in self.repo.list_telegram_digest_targets():
            user_id = int(identity.user_id)
            prefs = preference.data if preference and isinstance(preference.data, dict) else {}
            config = self._get_digest_config(prefs)
            if not config["enabled"] or not config["tracked_currencies"]:
                continue
            if not self._is_due_now(config):
                continue
            self.refresh_service.refresh_user_tracked_rates(user_id=user_id, prefs=prefs)
            overview = self.currency_service.get_overview(user_id=user_id, trades_limit=10)
            text = self.build_digest_text(overview=overview, config=config)
            deliveries.append(
                TelegramCurrencyDigestDelivery(
                    chat_id=str(identity.provider_user_id),
                    text=text,
                    user_id=user_id,
                    tracked_currencies=list(config["tracked_currencies"]),
                )
            )
        return deliveries

    def mark_delivery_sent(self, delivery: TelegramCurrencyDigestDelivery) -> None:
        preference = self.preferences.get_or_create(delivery.user_id)
        prefs = dict(preference.data) if isinstance(preference.data, dict) else {}
        config = self._get_digest_config(prefs)
        currency_prefs = dict(prefs.get("currency")) if isinstance(prefs.get("currency"), dict) else {}
        now_local = datetime.now(config["timezone"])
        currency_prefs["last_digest_sent_on"] = now_local.date().isoformat()
        prefs["currency"] = currency_prefs
        preference.data = prefs
        self.db.commit()
        log_background_job_event(
            "currency_digest",
            "digest_marked_sent",
            user_id=delivery.user_id,
            tracked_count=len(delivery.tracked_currencies),
            sent_on=currency_prefs["last_digest_sent_on"],
        )

    def build_digest_text(self, *, overview: dict, config: dict) -> str:
        lines = [title(ICON_CURRENCY, "Курсы и валютный портфель на сегодня")]
        current_rates = {
            str(item["currency"]).upper(): item
            for item in overview.get("current_rates") or []
        }
        positions = {
            str(item["currency"]).upper(): item
            for item in overview.get("positions") or []
        }
        base_currency = str(overview.get("base_currency") or "BYN")
        for currency in config["tracked_currencies"]:
            rate_row = current_rates.get(currency)
            position_row = positions.get(currency)
            if rate_row:
                line_icon = "ℹ️"
                rate_part = f"{currency}: курс {Decimal(rate_row['rate']):.4f}"
                if rate_row.get("change_value") is not None:
                    delta = Decimal(rate_row["change_value"])
                    line_icon = trend_icon(delta)
                    rate_part += f", {signed_decimal(delta, places=4)} за день"
            else:
                line_icon = "ℹ️"
                rate_part = f"{currency}: курс пока не задан"
            if position_row:
                result_value = Decimal(position_row["result_value"])
                if result_value:
                    line_icon = trend_icon(result_value)
                rate_part += (
                    f", позиция {Decimal(position_row['quantity']):.2f} {currency}, "
                    f"оценка {Decimal(position_row['current_value']):.2f} {base_currency}, "
                    f"результат {signed_decimal(result_value, places=2)} {base_currency}"
                )
            lines.append(f"{line_icon} {rate_part}")
        total_value = Decimal(overview.get("total_current_value") or 0)
        total_result = Decimal(overview.get("total_result_value") or 0)
        lines.append(
            f"{trend_icon(total_result)} Итого: оценка {total_value:.2f} {base_currency}, результат {signed_decimal(total_result, places=2)} {base_currency}"
        )
        return "\n".join(lines)

    def _get_digest_config(self, prefs: dict) -> dict:
        currency_prefs = prefs.get("currency") if isinstance(prefs.get("currency"), dict) else {}
        ui_prefs = prefs.get("ui") if isinstance(prefs.get("ui"), dict) else {}
        timezone_name = str(ui_prefs.get("timezone") or "").strip()
        if not timezone_name or timezone_name == "auto":
            timezone_name = str(ui_prefs.get("browser_timezone") or "").strip()
        timezone_obj = ZoneInfo(timezone_name or "Europe/Minsk")
        tracked = currency_prefs.get("tracked_currencies")
        if not isinstance(tracked, list):
            tracked = list(self.currency_service.DEFAULT_TRACKED_CURRENCIES)
        return {
            "enabled": currency_prefs.get("telegram_digest_enabled", False) is True,
            "time": str(currency_prefs.get("telegram_digest_time") or "10:00"),
            "timezone": timezone_obj,
            "tracked_currencies": [str(item).strip().upper() for item in tracked if str(item).strip()],
            "last_digest_sent_on": str(currency_prefs.get("last_digest_sent_on") or "").strip(),
        }

    def _is_due_now(self, config: dict) -> bool:
        now_local = datetime.now(config["timezone"])
        time_str = str(config["time"] or "10:00")
        try:
            hours_str, minutes_str = time_str.split(":", 1)
            reminder_hour = int(hours_str)
            reminder_minute = int(minutes_str)
        except (ValueError, TypeError):
            reminder_hour = 10
            reminder_minute = 0
        if config.get("last_digest_sent_on") == now_local.date().isoformat():
            return False
        return (now_local.hour, now_local.minute) >= (reminder_hour, reminder_minute)
