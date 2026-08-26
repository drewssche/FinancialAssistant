from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.logging import log_background_job_event
from app.repositories.currency_repo import CurrencyRepository
from app.repositories.preference_repo import PreferenceRepository
from app.services.activity_service import ActivityService
from app.services.bank_currency_rate_refresh_service import BankCurrencyRateRefreshService
from app.services.bank_currency_rate_registry import display_scale
from app.services.currency_rate_refresh_service import CurrencyRateRefreshService
from app.services.currency_service import CurrencyService
from app.services.telegram_currency_digest_chart_data_service import TelegramCurrencyDigestChartDataService
from app.services.telegram_currency_digest_chart_renderer import TelegramCurrencyDigestChartRenderer
from app.services.telegram_message_format import ICON_CURRENCY, signed_decimal, title, trend_icon


@dataclass(frozen=True)
class TelegramCurrencyDigestDelivery:
    chat_id: str
    text: str
    user_id: int
    tracked_currencies: list[str]
    photo_png: bytes | None = None
    photo_caption: str | None = None


class TelegramCurrencyDigestBotService:
    PHOTO_CAPTION_LIMIT = 1024

    def __init__(self, db: Session):
        self.db = db
        self.repo = CurrencyRepository(db)
        self.preferences = PreferenceRepository(db)
        self.currency_service = CurrencyService(db)
        self.refresh_service = CurrencyRateRefreshService(db)
        self.bank_refresh_service = BankCurrencyRateRefreshService(db)
        self.chart_data_service = TelegramCurrencyDigestChartDataService(db)
        self.chart_renderer: TelegramCurrencyDigestChartRenderer | None = None
        self.activity = ActivityService(db)

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
            self.bank_refresh_service.refresh_user_selected_rates(user_id=user_id, prefs=prefs)
            overview = self.currency_service.get_overview(user_id=user_id, trades_limit=10)
            text = self.build_digest_text(overview=overview, config=config)
            photo_png = self._build_chart_png(
                user_id=user_id,
                overview=overview,
                config=config,
            )
            deliveries.append(
                TelegramCurrencyDigestDelivery(
                    chat_id=str(identity.provider_user_id),
                    text=text,
                    user_id=user_id,
                    tracked_currencies=list(config["tracked_currencies"]),
                    photo_png=photo_png,
                    photo_caption=self.build_photo_caption(text) if photo_png else None,
                )
            )
        return deliveries

    def mark_delivery_sent(
        self,
        delivery: TelegramCurrencyDigestDelivery,
        *,
        delivery_format: str = "text",
    ) -> None:
        preference = self.preferences.get_or_create(delivery.user_id)
        prefs = dict(preference.data) if isinstance(preference.data, dict) else {}
        config = self._get_digest_config(prefs)
        currency_prefs = dict(prefs.get("currency")) if isinstance(prefs.get("currency"), dict) else {}
        now_local = datetime.now(config["timezone"])
        currency_prefs["last_digest_sent_on"] = now_local.date().isoformat()
        currency_prefs.pop("digest_delivery_claimed_on", None)
        prefs["currency"] = currency_prefs
        preference.data = prefs
        self.activity.record(
            user_id=delivery.user_id,
            actor_user_id=None,
            entity_type="currency_portfolio",
            entity_id=delivery.user_id,
            event_type="telegram_sent",
            title="Валютный дайджест Telegram отправлен",
            source="telegram",
            created_at=now_local,
            metadata={
                "message_type": "currency_digest",
                "sent_at": now_local.isoformat(),
                "chat_id": delivery.chat_id,
                "tracked_currencies": delivery.tracked_currencies,
                "delivery_format": delivery_format,
            },
        )
        self.db.commit()
        log_background_job_event(
            "currency_digest",
            "digest_marked_sent",
            user_id=delivery.user_id,
            tracked_count=len(delivery.tracked_currencies),
            sent_on=currency_prefs["last_digest_sent_on"],
            delivery_format=delivery_format,
        )

    def claim_delivery(self, delivery: TelegramCurrencyDigestDelivery) -> bool:
        preference = self.preferences.get_or_create(delivery.user_id)
        prefs = dict(preference.data) if isinstance(preference.data, dict) else {}
        config = self._get_digest_config(prefs)
        today = datetime.now(config["timezone"]).date().isoformat()
        if config.get("last_digest_sent_on") == today or config.get("digest_delivery_claimed_on") == today:
            return False
        currency_prefs = dict(prefs.get("currency")) if isinstance(prefs.get("currency"), dict) else {}
        currency_prefs["digest_delivery_claimed_on"] = today
        prefs["currency"] = currency_prefs
        preference.data = prefs
        self.db.commit()
        log_background_job_event(
            "currency_digest",
            "digest_delivery_claimed",
            user_id=delivery.user_id,
            claimed_on=today,
        )
        return True

    def release_delivery(self, delivery: TelegramCurrencyDigestDelivery) -> None:
        preference = self.preferences.get_or_create(delivery.user_id)
        prefs = dict(preference.data) if isinstance(preference.data, dict) else {}
        currency_prefs = dict(prefs.get("currency")) if isinstance(prefs.get("currency"), dict) else {}
        currency_prefs.pop("digest_delivery_claimed_on", None)
        prefs["currency"] = currency_prefs
        preference.data = prefs
        self.db.commit()

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
        bank_rates = [item for item in overview.get("bank_rates") or [] if not item.get("stale")]
        base_currency = str(overview.get("base_currency") or "BYN")
        for currency in config["tracked_currencies"]:
            rate_row = current_rates.get(currency)
            position_row = positions.get(currency)
            if rate_row:
                line_icon = "ℹ️"
                scale = display_scale(currency)
                rate = Decimal(rate_row["rate"]) * scale
                currency_label = f"{scale} {currency}" if scale > 1 else currency
                rate_part = f"{currency_label}: курс НБРБ {rate:.4f}"
                if rate_row.get("change_value") is not None:
                    delta = Decimal(rate_row["change_value"]) * scale
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
            currency_bank_rates = [item for item in bank_rates if item.get("currency") == currency]
            if currency_bank_rates:
                best_buy = max(currency_bank_rates, key=lambda item: Decimal(item["buy_rate"]))
                best_sell = min(currency_bank_rates, key=lambda item: Decimal(item["sell_rate"]))
                lines.append(
                    "🏦 Банки: покупка "
                    f"{Decimal(best_buy['buy_rate']):.4f} в {best_buy['bank_name']}; "
                    f"продажа {Decimal(best_sell['sell_rate']):.4f} в {best_sell['bank_name']}"
                )
        total_value = Decimal(overview.get("total_current_value") or 0)
        total_result = Decimal(overview.get("total_result_value") or 0)
        lines.append(
            f"{trend_icon(total_result)} Итого: оценка {total_value:.2f} {base_currency}, результат {signed_decimal(total_result, places=2)} {base_currency}"
        )
        return "\n".join(lines)

    def build_photo_caption(self, text: str) -> str:
        normalized = str(text or "").strip()
        if self._telegram_text_units(normalized) <= self.PHOTO_CAPTION_LIMIT:
            return normalized
        suffix = "\n… Остальные детали — в приложении."
        available = self.PHOTO_CAPTION_LIMIT - self._telegram_text_units(suffix)
        kept_lines = []
        for line in normalized.splitlines():
            candidate = "\n".join([*kept_lines, line])
            if self._telegram_text_units(candidate) > available:
                break
            kept_lines.append(line)
        if kept_lines:
            return "\n".join(kept_lines) + suffix
        return self._truncate_to_telegram_units(normalized, available).rstrip() + suffix

    @staticmethod
    def _telegram_text_units(value: str) -> int:
        return len(value.encode("utf-16-le")) // 2

    @classmethod
    def _truncate_to_telegram_units(cls, value: str, limit: int) -> str:
        if limit <= 0:
            return ""
        lower = 0
        upper = len(value)
        while lower < upper:
            middle = (lower + upper + 1) // 2
            if cls._telegram_text_units(value[:middle]) <= limit:
                lower = middle
            else:
                upper = middle - 1
        return value[:lower]

    def _build_chart_png(self, *, user_id: int, overview: dict, config: dict) -> bytes | None:
        if not config["chart_enabled"]:
            return None
        try:
            now_local = datetime.now(config["timezone"])
            payload = self.chart_data_service.build_payload(
                user_id=user_id,
                tracked_currencies=config["tracked_currencies"],
                bank_codes=config["bank_rate_banks"],
                overview=overview,
                as_of=now_local.date(),
            )
            if self.chart_renderer is None:
                self.chart_renderer = TelegramCurrencyDigestChartRenderer()
            return self.chart_renderer.render(payload)
        except Exception as exc:  # noqa: BLE001 - a text digest must remain available.
            log_background_job_event(
                "currency_digest",
                "chart_render_failed",
                user_id=user_id,
                error_type=type(exc).__name__,
            )
            return None

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
            "bank_rate_banks": list(currency_prefs.get("bank_rate_banks") or []),
            "chart_enabled": currency_prefs.get("telegram_digest_chart_enabled", True) is not False,
            "last_digest_sent_on": str(currency_prefs.get("last_digest_sent_on") or "").strip(),
            "digest_delivery_claimed_on": str(currency_prefs.get("digest_delivery_claimed_on") or "").strip(),
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
        today = now_local.date().isoformat()
        if config.get("last_digest_sent_on") == today or config.get("digest_delivery_claimed_on") == today:
            return False
        return (now_local.hour, now_local.minute) >= (reminder_hour, reminder_minute)
