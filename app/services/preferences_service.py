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
        item = self.repo.update(user_id=user_id, preferences_version=preferences_version, data=data)
        self.plan_reminder_service.sync_user_jobs(user_id=user_id)
        self.debt_reminder_service.sync_user_jobs(user_id=user_id)
        self.db.commit()
        self.db.refresh(item)
        plans_prefs = data.get("plans") if isinstance(data.get("plans"), dict) else {}
        ui_prefs = data.get("ui") if isinstance(data.get("ui"), dict) else {}
        log_background_job_event(
            "preferences",
            "preferences_updated",
            user_id=user_id,
            preferences_version=preferences_version,
            reminders_enabled=plans_prefs.get("reminders_enabled", True),
            reminder_time=plans_prefs.get("reminder_time", "09:00"),
            timezone=ui_prefs.get("timezone", "auto"),
        )
        return item
