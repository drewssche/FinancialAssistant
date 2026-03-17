from sqlalchemy.orm import Session

from app.repositories.preference_repo import PreferenceRepository
from app.services.plan_reminder_service import PlanReminderService


class PreferencesService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PreferenceRepository(db)
        self.plan_reminder_service = PlanReminderService(db)

    def get_preferences(self, user_id: int):
        return self.repo.get_or_create(user_id)

    def update_preferences(self, user_id: int, preferences_version: int, data: dict):
        item = self.repo.update(user_id=user_id, preferences_version=preferences_version, data=data)
        self.plan_reminder_service.sync_user_jobs(user_id=user_id)
        self.db.commit()
        self.db.refresh(item)
        return item
