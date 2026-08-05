from sqlalchemy.orm import Session

from app.core.logging import log_background_job_event
from app.repositories.preference_repo import PreferenceRepository
from app.services.debt_reminder_service import DebtReminderService
from app.services.plan_reminder_service import PlanReminderService


class PreferencesService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PreferenceRepository(db)
        self.plan_reminder_service = PlanReminderService(db)
        self.debt_reminder_service = DebtReminderService(db)

    def get_preferences(self, user_id: int):
        return self.repo.get_or_create(user_id)

    def update_preferences(self, user_id: int, preferences_version: int, data: dict):
        current = self.repo.get_or_create(user_id)
        merged_data = self._preserve_currency_runtime_state(current.data, data)
        item = self.repo.update(user_id=user_id, preferences_version=preferences_version, data=merged_data)
        self.plan_reminder_service.sync_user_jobs(user_id=user_id)
        self.debt_reminder_service.sync_user_jobs(user_id=user_id)
        self.db.commit()
        self.db.refresh(item)
        plans_prefs = data.get("plans") if isinstance(data.get("plans"), dict) else {}
        debts_prefs = data.get("debts") if isinstance(data.get("debts"), dict) else {}
        ui_prefs = data.get("ui") if isinstance(data.get("ui"), dict) else {}
        log_background_job_event(
            "preferences",
            "preferences_updated",
            user_id=user_id,
            preferences_version=preferences_version,
            plan_reminders_enabled=plans_prefs.get("reminders_enabled", True),
            plan_reminder_time=plans_prefs.get("reminder_time", "09:00"),
            debt_reminders_enabled=debts_prefs.get("reminders_enabled", plans_prefs.get("reminders_enabled", True)),
            debt_reminder_time=debts_prefs.get("reminder_time", plans_prefs.get("reminder_time", "09:00")),
            timezone=ui_prefs.get("timezone", "auto"),
        )
        return item

    @staticmethod
    def _preserve_currency_runtime_state(current_data: dict, incoming_data: dict) -> dict:
        """Keep bot-owned delivery markers out of the browser's stale-write path."""
        current_data = current_data if isinstance(current_data, dict) else {}
        merged = dict(incoming_data or {})
        current_currency = current_data.get("currency") if isinstance(current_data.get("currency"), dict) else {}
        incoming_currency = merged.get("currency") if isinstance(merged.get("currency"), dict) else {}
        next_currency = dict(incoming_currency)

        for key in ("last_digest_sent_on", "digest_delivery_claimed_on"):
            if current_currency.get(key):
                next_currency[key] = current_currency[key]
            else:
                next_currency.pop(key, None)

        current_alerts = current_currency.get("currency_alerts") if isinstance(current_currency.get("currency_alerts"), dict) else {}
        incoming_alerts = next_currency.get("currency_alerts") if isinstance(next_currency.get("currency_alerts"), dict) else {}
        merged_alerts = {}
        for currency, incoming_config in incoming_alerts.items():
            if not isinstance(incoming_config, dict):
                continue
            next_config = dict(incoming_config)
            current_config = current_alerts.get(currency) if isinstance(current_alerts.get(currency), dict) else {}
            for direction in ("above", "below"):
                threshold_key = f"{direction}_rate"
                marker_key = f"last_{direction}_marker"
                if str(next_config.get(threshold_key) or "").strip() == str(current_config.get(threshold_key) or "").strip():
                    next_config[marker_key] = str(current_config.get(marker_key) or "")
                else:
                    next_config[marker_key] = ""
            merged_alerts[currency] = next_config
        next_currency["currency_alerts"] = merged_alerts
        merged["currency"] = next_currency
        return merged
