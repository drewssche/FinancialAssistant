from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.currency_repo import CurrencyRepository
from app.schemas.admin import AdminCurrencyDiagnosticsItem, AdminCurrencyDiagnosticsOut
from app.services.currency_service import CurrencyService


class AdminCurrencyRuntimeService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CurrencyRepository(db)
        self.currency_service = CurrencyService(db)

    def get_diagnostics(self) -> AdminCurrencyDiagnosticsOut:
        today = date.today()
        preferences = self.repo.list_currency_preferences()
        tracked_users = 0
        tracked_currency_slots = 0
        digest_enabled_users = 0
        alert_rules_count = 0
        stale_slots = 0
        missing_slots = 0
        freshest_rate_date: date | None = None
        items_by_currency: dict[str, dict] = {}

        for preference in preferences:
            prefs = preference.data if isinstance(preference.data, dict) else {}
            config = self.currency_service.get_currency_preferences(preference.user_id)
            tracked = list(config["tracked_currencies"])
            if tracked:
                tracked_users += 1
            raw_currency_prefs = prefs.get("currency") if isinstance(prefs.get("currency"), dict) else {}
            digest_enabled = raw_currency_prefs.get("telegram_digest_enabled", False) is True and bool(tracked)
            if digest_enabled:
                digest_enabled_users += 1
            raw_alerts = raw_currency_prefs.get("currency_alerts") if isinstance(raw_currency_prefs.get("currency_alerts"), dict) else {}
            latest_rate_map = self.repo.get_latest_rate_map(user_id=preference.user_id)

            for currency in tracked:
                tracked_currency_slots += 1
                item = items_by_currency.setdefault(
                    currency,
                    {
                        "currency": currency,
                        "tracked_users": 0,
                        "digest_users": 0,
                        "alert_rules": 0,
                        "latest_rate": None,
                        "latest_rate_date": None,
                        "stale_users": 0,
                        "missing_users": 0,
                    },
                )
                item["tracked_users"] += 1
                if digest_enabled:
                    item["digest_users"] += 1

                alert_config = raw_alerts.get(currency) if isinstance(raw_alerts.get(currency), dict) else {}
                currency_alert_rules = 0
                if str(alert_config.get("above_rate") or "").strip():
                    currency_alert_rules += 1
                if str(alert_config.get("below_rate") or "").strip():
                    currency_alert_rules += 1
                item["alert_rules"] += currency_alert_rules
                alert_rules_count += currency_alert_rules

                latest_row = latest_rate_map.get(currency)
                if not latest_row:
                    item["missing_users"] += 1
                    missing_slots += 1
                    continue

                latest_date = latest_row.rate_date
                if freshest_rate_date is None or latest_date > freshest_rate_date:
                    freshest_rate_date = latest_date
                if item["latest_rate_date"] is None or latest_date.isoformat() > str(item["latest_rate_date"]):
                    item["latest_rate"] = Decimal(latest_row.rate)
                    item["latest_rate_date"] = latest_date.isoformat()
                if latest_date < today:
                    item["stale_users"] += 1
                    stale_slots += 1

        items = [
            AdminCurrencyDiagnosticsItem(
                currency=str(raw["currency"]),
                tracked_users=int(raw["tracked_users"]),
                digest_users=int(raw["digest_users"]),
                alert_rules=int(raw["alert_rules"]),
                latest_rate=Decimal(raw["latest_rate"]) if raw["latest_rate"] is not None else None,
                latest_rate_date=str(raw["latest_rate_date"]) if raw["latest_rate_date"] else None,
                stale_users=int(raw["stale_users"]),
                missing_users=int(raw["missing_users"]),
            )
            for _, raw in sorted(items_by_currency.items())
        ]
        return AdminCurrencyDiagnosticsOut(
            tracked_users=tracked_users,
            tracked_currency_slots=tracked_currency_slots,
            digest_enabled_users=digest_enabled_users,
            alert_rules_count=alert_rules_count,
            stale_slots=stale_slots,
            missing_slots=missing_slots,
            freshest_rate_date=freshest_rate_date.isoformat() if freshest_rate_date else None,
            items=items,
        )
