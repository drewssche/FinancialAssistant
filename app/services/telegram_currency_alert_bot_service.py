from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.logging import log_background_job_event
from app.repositories.currency_repo import CurrencyRepository
from app.repositories.preference_repo import PreferenceRepository
from app.services.activity_service import ActivityService
from app.services.bank_currency_rate_refresh_service import BankCurrencyRateRefreshService
from app.services.bank_currency_rate_registry import BANK_RATE_PROVIDERS, display_scale
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
class BankCurrencyAlertTrigger:
    rule_id: str
    currency: str
    rate_kind: str
    direction: str
    threshold: Decimal
    current_rate: Decimal
    bank_code: str
    bank_name: str
    quoted_at: str
    marker: str


@dataclass(frozen=True)
class TelegramCurrencyAlertDelivery:
    chat_id: str
    text: str
    user_id: int
    triggers: list[CurrencyAlertTrigger]
    bank_triggers: list[BankCurrencyAlertTrigger] = field(default_factory=list)


class TelegramCurrencyAlertBotService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CurrencyRepository(db)
        self.preferences = PreferenceRepository(db)
        self.currency_service = CurrencyService(db)
        self.refresh_service = CurrencyRateRefreshService(db)
        self.bank_refresh_service = BankCurrencyRateRefreshService(db)
        self.activity = ActivityService(db)

    def list_due_deliveries(self) -> list[TelegramCurrencyAlertDelivery]:
        deliveries: list[TelegramCurrencyAlertDelivery] = []
        for identity, preference in self.repo.list_telegram_digest_targets():
            user_id = int(identity.user_id)
            prefs = preference.data if preference and isinstance(preference.data, dict) else {}
            config = self._get_alerts_config(prefs)
            if not config["alerts"] and not config["bank_alerts"]:
                continue
            if config["alerts"]:
                self.refresh_service.refresh_user_tracked_rates(user_id=user_id, prefs=prefs)
            if config["bank_alerts"]:
                self.bank_refresh_service.refresh_user_selected_rates(user_id=user_id, prefs=prefs)
            overview = self.currency_service.get_overview(user_id=user_id, trades_limit=10)
            current_rates = {
                str(item["currency"]).upper(): item
                for item in overview.get("current_rates") or []
            }
            triggers, rearmed, suppressed = self._collect_triggers(current_rates=current_rates, config=config)
            bank_triggers, bank_rearmed, bank_suppressed = self._collect_bank_triggers(
                bank_rates=overview.get("bank_rates") or [],
                config=config,
            )
            if rearmed:
                self._persist_rearmed_directions(user_id=user_id, rearmed=rearmed)
            if bank_rearmed:
                self._persist_rearmed_bank_rules(user_id=user_id, rule_ids=bank_rearmed)
            if suppressed:
                log_background_job_event(
                    "currency_alerts",
                    "alerts_suppressed",
                    user_id=user_id,
                    trigger_count=len(suppressed),
                    directions=sorted({direction for _, direction in suppressed}),
                )
            if bank_suppressed:
                log_background_job_event(
                    "currency_alerts",
                    "bank_alerts_suppressed",
                    user_id=user_id,
                    trigger_count=len(bank_suppressed),
                )
            if not triggers and not bank_triggers:
                continue
            log_background_job_event(
                "currency_alerts",
                "alerts_triggered",
                user_id=user_id,
                trigger_count=len(triggers) + len(bank_triggers),
                directions=sorted(
                    {trigger.direction for trigger in triggers}
                    | {trigger.direction for trigger in bank_triggers}
                ),
            )
            deliveries.append(
                TelegramCurrencyAlertDelivery(
                    chat_id=str(identity.provider_user_id),
                    text=self.build_alert_text(
                        triggers=triggers,
                        bank_triggers=bank_triggers,
                        base_currency=str(overview.get("base_currency") or "BYN"),
                    ),
                    user_id=user_id,
                    triggers=triggers,
                    bank_triggers=bank_triggers,
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
        raw_bank_alerts = currency_prefs.get("bank_rate_alerts")
        bank_alerts = [dict(item) for item in raw_bank_alerts or [] if isinstance(item, dict)]
        bank_alerts_by_id = {str(item.get("id") or ""): item for item in bank_alerts}
        for trigger in delivery.bank_triggers:
            config = bank_alerts_by_id.get(trigger.rule_id)
            if config is None:
                continue
            marker_key = f"last_{trigger.direction}_marker"
            config[marker_key] = trigger.marker
            self.activity.record(
                user_id=delivery.user_id,
                actor_user_id=None,
                entity_type="currency_portfolio",
                entity_id=delivery.user_id,
                event_type="telegram_sent",
                title="Банковский валютный алерт Telegram отправлен",
                source="telegram",
                metadata={
                    "message_type": "bank_currency_alert",
                    "chat_id": delivery.chat_id,
                    "currency": trigger.currency,
                    "rate_kind": trigger.rate_kind,
                    "direction": trigger.direction,
                    "threshold": str(trigger.threshold),
                    "current_rate": str(trigger.current_rate),
                    "bank_code": trigger.bank_code,
                    "bank_name": trigger.bank_name,
                    "marker": trigger.marker,
                },
            )
        currency_prefs["currency_alerts"] = alerts
        currency_prefs["bank_rate_alerts"] = bank_alerts
        prefs["currency"] = currency_prefs
        preference.data = prefs
        self.db.commit()
        log_background_job_event(
            "currency_alerts",
            "alerts_marked_sent",
            user_id=delivery.user_id,
            trigger_count=len(delivery.triggers) + len(delivery.bank_triggers),
        )

    def build_alert_text(
        self,
        *,
        triggers: list[CurrencyAlertTrigger],
        bank_triggers: list[BankCurrencyAlertTrigger] | None = None,
        base_currency: str,
    ) -> str:
        lines = [title(ICON_TARGET, "Сработали алерты по курсам валют")]
        for trigger in triggers:
            direction_text = "выше" if trigger.direction == "above" else "ниже"
            scale = display_scale(trigger.currency)
            currency_label = f"{scale} {trigger.currency}" if scale > 1 else trigger.currency
            lines.append(
                f"{threshold_icon(trigger.direction)} {currency_label}: курс {trigger.current_rate:.4f} {base_currency} {direction_text} порога {trigger.threshold:.4f} "
                f"(дата курса {trigger.rate_date})"
            )
        for trigger in bank_triggers or []:
            rate_kind_text = "покупки банка" if trigger.rate_kind == "buy" else "продажи банка"
            comparison_text = "выше" if trigger.direction == "above" else "ниже"
            scale = display_scale(trigger.currency)
            currency_label = f"{scale} {trigger.currency}" if scale > 1 else trigger.currency
            lines.append(
                f"🏦 {currency_label}: курс {rate_kind_text} {trigger.current_rate:.4f} {base_currency} "
                f"в {trigger.bank_name} — {comparison_text} порога {trigger.threshold:.4f}"
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
            scale = display_scale(currency)
            current_rate = Decimal(rate_row["rate"]) * scale
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

    def _collect_bank_triggers(
        self,
        *,
        bank_rates: list[dict],
        config: dict,
    ) -> tuple[
        list[BankCurrencyAlertTrigger],
        list[tuple[str, str]],
        list[tuple[str, str]],
    ]:
        triggers = []
        rearmed = []
        suppressed = []
        fresh_rates = [item for item in bank_rates if not item.get("stale")]
        for rule in config["bank_alerts"]:
            rows = [item for item in fresh_rates if item.get("currency") == rule["currency"]]
            if rule["bank_code"] != "best":
                rows = [item for item in rows if item.get("bank_code") == rule["bank_code"]]
            if not rows:
                continue
            rate_key = "buy_rate" if rule["rate_kind"] == "buy" else "sell_rate"
            selector = max if rule["rate_kind"] == "buy" else min
            row = selector(rows, key=lambda item: Decimal(item[rate_key]))
            current_rate = Decimal(row[rate_key])
            for direction in ("above", "below"):
                threshold = rule.get(f"{direction}_rate")
                if threshold is None:
                    continue
                matches = current_rate >= threshold if direction == "above" else current_rate <= threshold
                marker = self._active_marker(direction=direction, threshold=threshold)
                last_marker = rule.get(f"last_{direction}_marker")
                if matches:
                    if not self._marker_is_active(
                        last_marker,
                        direction=direction,
                        threshold=threshold,
                    ):
                        triggers.append(
                            BankCurrencyAlertTrigger(
                                rule_id=rule["id"],
                                currency=rule["currency"],
                                rate_kind=rule["rate_kind"],
                                direction=direction,
                                threshold=threshold,
                                current_rate=current_rate,
                                bank_code=str(row["bank_code"]),
                                bank_name=str(row["bank_name"]),
                                quoted_at=str(row.get("quoted_at") or row.get("fetched_at") or ""),
                                marker=marker,
                            )
                        )
                    else:
                        suppressed.append((rule["id"], direction))
                elif last_marker:
                    rearmed.append((rule["id"], direction))
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

    def _persist_rearmed_bank_rules(
        self,
        *,
        user_id: int,
        rule_ids: list[tuple[str, str]],
    ) -> None:
        preference = self.preferences.get_or_create(user_id)
        prefs = dict(preference.data) if isinstance(preference.data, dict) else {}
        currency_prefs = dict(prefs.get("currency")) if isinstance(prefs.get("currency"), dict) else {}
        raw_alerts = currency_prefs.get("bank_rate_alerts")
        alerts = [dict(item) for item in raw_alerts or [] if isinstance(item, dict)]
        wanted = set(rule_ids)
        changed = 0
        for alert in alerts:
            rule_id = str(alert.get("id") or "")
            for direction in ("above", "below"):
                marker_key = f"last_{direction}_marker"
                if (rule_id, direction) in wanted and alert.get(marker_key):
                    alert[marker_key] = ""
                    changed += 1
                elif (rule_id, direction) in wanted and alert.get("last_marker"):
                    alert["last_marker"] = ""
                    changed += 1
        if not changed:
            return
        currency_prefs["bank_rate_alerts"] = alerts
        prefs["currency"] = currency_prefs
        preference.data = prefs
        self.db.commit()
        log_background_job_event(
            "currency_alerts",
            "bank_alerts_rearmed",
            user_id=user_id,
            rule_count=changed,
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
        selected_banks = currency_prefs.get("bank_rate_banks")
        if not isinstance(selected_banks, list):
            selected_banks = list(BANK_RATE_PROVIDERS)
        allowed_banks = {
            str(item).strip().lower()
            for item in selected_banks
            if str(item).strip().lower() in BANK_RATE_PROVIDERS
        }
        bank_alerts = []
        for index, raw in enumerate(currency_prefs.get("bank_rate_alerts") or []):
            if not isinstance(raw, dict):
                continue
            legacy_action = str(raw.get("action") or "").strip().lower()
            rate_kind = str(raw.get("rate_kind") or "").strip().lower()
            if rate_kind not in {"buy", "sell"}:
                rate_kind = "buy" if legacy_action == "sell" else "sell"
            currency = str(raw.get("currency") or "").strip().upper()
            bank_code = str(raw.get("bank_code") or "best").strip().lower()
            above_rate = self._parse_rate(raw.get("above_rate"))
            below_rate = self._parse_rate(raw.get("below_rate"))
            legacy_threshold = self._parse_rate(raw.get("threshold"))
            last_above_marker = str(raw.get("last_above_marker") or "").strip()
            last_below_marker = str(raw.get("last_below_marker") or "").strip()
            if above_rate is None and below_rate is None and legacy_threshold is not None:
                if legacy_action == "sell":
                    above_rate = legacy_threshold
                    if raw.get("last_marker"):
                        last_above_marker = self._active_marker(
                            direction="above",
                            threshold=legacy_threshold,
                        )
                else:
                    below_rate = legacy_threshold
                    if raw.get("last_marker"):
                        last_below_marker = self._active_marker(
                            direction="below",
                            threshold=legacy_threshold,
                        )
            if (
                currency not in tracked_currencies
                or (above_rate is None and below_rate is None)
                or (bank_code != "best" and bank_code not in allowed_banks)
            ):
                continue
            bank_alerts.append(
                {
                    "id": str(raw.get("id") or f"bank-alert-{index}"),
                    "rate_kind": rate_kind,
                    "currency": currency,
                    "bank_code": bank_code,
                    "above_rate": above_rate,
                    "below_rate": below_rate,
                    "last_above_marker": last_above_marker,
                    "last_below_marker": last_below_marker,
                }
            )
        return {
            "alerts": alerts,
            "bank_alerts": bank_alerts,
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
