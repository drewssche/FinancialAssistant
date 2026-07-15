from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.logging import log_background_job_event
from app.repositories.currency_repo import CurrencyRepository
from app.repositories.preference_repo import PreferenceRepository
from app.services.activity_service import ActivityService
from app.services.currency_rate_refresh_service import CurrencyRateRefreshService
from app.services.currency_service import CurrencyService
from app.services.telegram_message_format import ICON_TARGET, threshold_icon, title


@dataclass(frozen=True)
class CurrencyAlertTrigger:
    currency: str
    direction: str
    threshold: Decimal
    current_rate: Decimal
    rate_date: str
    marker: str


@dataclass(frozen=True)
class TelegramCurrencyAlertDelivery:
    chat_id: str
    text: str
    user_id: int
    triggers: list[CurrencyAlertTrigger]


class TelegramCurrencyAlertBotService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CurrencyRepository(db)
        self.preferences = PreferenceRepository(db)
        self.currency_service = CurrencyService(db)
        self.refresh_service = CurrencyRateRefreshService(db)
        self.activity = ActivityService(db)

    def list_due_deliveries(self) -> list[TelegramCurrencyAlertDelivery]:
        deliveries: list[TelegramCurrencyAlertDelivery] = []
        for identity, preference in self.repo.list_telegram_digest_targets():
            user_id = int(identity.user_id)
            prefs = preference.data if preference and isinstance(preference.data, dict) else {}
            config = self._get_alerts_config(prefs)
            if not config["alerts"]:
                continue
            self.refresh_service.refresh_user_tracked_rates(user_id=user_id, prefs=prefs)
            overview = self.currency_service.get_overview(user_id=user_id, trades_limit=10)
            current_rates = {
                str(item["currency"]).upper(): item
                for item in overview.get("current_rates") or []
            }
            triggers, rearmed, suppressed = self._collect_triggers(current_rates=current_rates, config=config)
            if rearmed:
                self._persist_rearmed_directions(user_id=user_id, rearmed=rearmed)
            if suppressed:
                log_background_job_event(
                    "currency_alerts",
                    "alerts_suppressed",
                    user_id=user_id,
                    trigger_count=len(suppressed),
                    directions=sorted({direction for _, direction in suppressed}),
                )
            if not triggers:
                continue
            log_background_job_event(
                "currency_alerts",
                "alerts_triggered",
                user_id=user_id,
                trigger_count=len(triggers),
                directions=sorted({trigger.direction for trigger in triggers}),
            )
            deliveries.append(
                TelegramCurrencyAlertDelivery(
                    chat_id=str(identity.provider_user_id),
                    text=self.build_alert_text(triggers=triggers, base_currency=str(overview.get("base_currency") or "BYN")),
                    user_id=user_id,
                    triggers=triggers,
                )
            )
        return deliveries

    def mark_delivery_sent(self, delivery: TelegramCurrencyAlertDelivery) -> None:
        preference = self.preferences.get_or_create(delivery.user_id)
        prefs = dict(preference.data) if isinstance(preference.data, dict) else {}
        currency_prefs = dict(prefs.get("currency")) if isinstance(prefs.get("currency"), dict) else {}
        raw_alerts = currency_prefs.get("currency_alerts") if isinstance(currency_prefs.get("currency_alerts"), dict) else {}
        alerts = {str(code).upper(): dict(value) for code, value in raw_alerts.items() if isinstance(value, dict)}
        for trigger in delivery.triggers:
            config = alerts.setdefault(trigger.currency, {})
            key = "last_above_marker" if trigger.direction == "above" else "last_below_marker"
            config[key] = trigger.marker
            self.activity.record(
                user_id=delivery.user_id,
                actor_user_id=None,
                entity_type="currency_portfolio",
                entity_id=delivery.user_id,
                event_type="telegram_sent",
                title="Валютный алерт Telegram отправлен",
                source="telegram",
                metadata={
                    "message_type": "currency_alert",
                    "chat_id": delivery.chat_id,
                    "currency": trigger.currency,
                    "direction": trigger.direction,
                    "threshold": str(trigger.threshold),
                    "current_rate": str(trigger.current_rate),
                    "rate_date": trigger.rate_date,
                    "marker": trigger.marker,
                },
            )
        currency_prefs["currency_alerts"] = alerts
        prefs["currency"] = currency_prefs
        preference.data = prefs
        self.db.commit()
        log_background_job_event(
            "currency_alerts",
            "alerts_marked_sent",
            user_id=delivery.user_id,
            trigger_count=len(delivery.triggers),
        )

    def build_alert_text(self, *, triggers: list[CurrencyAlertTrigger], base_currency: str) -> str:
        lines = [title(ICON_TARGET, "Сработали алерты по курсам валют")]
        for trigger in triggers:
            direction_text = "выше" if trigger.direction == "above" else "ниже"
            lines.append(
                f"{threshold_icon(trigger.direction)} {trigger.currency}: курс {trigger.current_rate:.4f} {base_currency} {direction_text} порога {trigger.threshold:.4f} "
                f"(дата курса {trigger.rate_date})"
            )
        return "\n".join(lines)

    def _collect_triggers(
        self,
        *,
        current_rates: dict[str, dict],
        config: dict,
    ) -> tuple[list[CurrencyAlertTrigger], list[tuple[str, str]], list[tuple[str, str]]]:
        triggers: list[CurrencyAlertTrigger] = []
        rearmed: list[tuple[str, str]] = []
        suppressed: list[tuple[str, str]] = []
        for currency, alert in config["alerts"].items():
            rate_row = current_rates.get(currency)
            if not rate_row:
                continue
            current_rate = Decimal(rate_row["rate"])
            rate_date = str(rate_row.get("rate_date") or "")
            above_rate = alert.get("above_rate")
            if above_rate is not None:
                marker = self._active_marker(direction="above", threshold=above_rate)
                last_marker = str(alert.get("last_above_marker") or "")
                if current_rate >= above_rate:
                    if not self._marker_is_active(last_marker, direction="above", threshold=above_rate):
                        triggers.append(
                            CurrencyAlertTrigger(
                                currency=currency,
                                direction="above",
                                threshold=above_rate,
                                current_rate=current_rate,
                                rate_date=rate_date,
                                marker=marker,
                            )
                        )
                    else:
                        suppressed.append((currency, "above"))
                elif last_marker:
                    rearmed.append((currency, "above"))
            below_rate = alert.get("below_rate")
            if below_rate is not None:
                marker = self._active_marker(direction="below", threshold=below_rate)
                last_marker = str(alert.get("last_below_marker") or "")
                if current_rate <= below_rate:
                    if not self._marker_is_active(last_marker, direction="below", threshold=below_rate):
                        triggers.append(
                            CurrencyAlertTrigger(
                                currency=currency,
                                direction="below",
                                threshold=below_rate,
                                current_rate=current_rate,
                                rate_date=rate_date,
                                marker=marker,
                            )
                        )
                    else:
                        suppressed.append((currency, "below"))
                elif last_marker:
                    rearmed.append((currency, "below"))
        return triggers, rearmed, suppressed

    def _persist_rearmed_directions(self, *, user_id: int, rearmed: list[tuple[str, str]]) -> None:
        preference = self.preferences.get_or_create(user_id)
        prefs = dict(preference.data) if isinstance(preference.data, dict) else {}
        currency_prefs = dict(prefs.get("currency")) if isinstance(prefs.get("currency"), dict) else {}
        raw_alerts = currency_prefs.get("currency_alerts") if isinstance(currency_prefs.get("currency_alerts"), dict) else {}
        alerts = {str(code).upper(): dict(value) for code, value in raw_alerts.items() if isinstance(value, dict)}
        changed = 0
        for currency, direction in rearmed:
            config = alerts.get(currency)
            if not config:
                continue
            key = "last_above_marker" if direction == "above" else "last_below_marker"
            if config.get(key):
                config[key] = ""
                changed += 1
        if not changed:
            return
        currency_prefs["currency_alerts"] = alerts
        prefs["currency"] = currency_prefs
        preference.data = prefs
        self.db.commit()
        log_background_job_event(
            "currency_alerts",
            "alerts_rearmed",
            user_id=user_id,
            direction_count=changed,
        )

    @staticmethod
    def _active_marker(*, direction: str, threshold: Decimal) -> str:
        return f"active:{direction}:{threshold:.6f}"

    @staticmethod
    def _marker_is_active(marker: str, *, direction: str, threshold: Decimal) -> bool:
        raw = str(marker or "").strip()
        if not raw:
            return False
        parts = raw.split(":")
        if len(parts) < 3 or parts[-2] != direction:
            return False
        try:
            marker_threshold = Decimal(parts[-1])
        except Exception:  # noqa: BLE001
            return False
        return marker_threshold == threshold

    def _get_alerts_config(self, prefs: dict) -> dict:
        currency_prefs = prefs.get("currency") if isinstance(prefs.get("currency"), dict) else {}
        tracked = currency_prefs.get("tracked_currencies")
        tracked_currencies = {
            str(item).strip().upper()
            for item in (tracked if isinstance(tracked, list) else [])
            if str(item).strip()
        }
        raw_alerts = currency_prefs.get("currency_alerts") if isinstance(currency_prefs.get("currency_alerts"), dict) else {}
        alerts = {}
        for currency, raw in raw_alerts.items():
            code = str(currency or "").strip().upper()
            if not code or code not in tracked_currencies or not isinstance(raw, dict):
                continue
            above_rate = self._parse_rate(raw.get("above_rate"))
            below_rate = self._parse_rate(raw.get("below_rate"))
            if above_rate is None and below_rate is None:
                continue
            alerts[code] = {
                "above_rate": above_rate,
                "below_rate": below_rate,
                "last_above_marker": str(raw.get("last_above_marker") or "").strip(),
                "last_below_marker": str(raw.get("last_below_marker") or "").strip(),
            }
        return {
            "alerts": alerts,
        }

    @staticmethod
    def _parse_rate(value) -> Decimal | None:
        raw = str(value or "").strip().replace(",", ".")
        if not raw:
            return None
        try:
            rate = Decimal(raw)
        except Exception:  # noqa: BLE001
            return None
        if rate <= 0:
            return None
        return rate.quantize(Decimal("0.000001"))
