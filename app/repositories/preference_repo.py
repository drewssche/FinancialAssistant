from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UserPreference


class PreferenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user_id: int) -> UserPreference:
        item = self.db.scalar(select(UserPreference).where(UserPreference.user_id == user_id))
        if item:
            return item
        item = UserPreference(
            user_id=user_id,
            preferences_version=1,
            data={
                "dashboard": {"period": "day"},
                "operations": {"filters": {}, "sort": "operation_date:desc"},
                "analytics": {
                    "top_operations_limit": 5,
                    "top_positions_limit": 10,
                },
                "admin": {
                    "user_status_filter": "pending",
                },
                "ui": {
                    "timezone": "auto",
                    "currency": "BYN",
                    "currency_position": "suffix",
                    "show_dashboard_analytics": True,
                    "show_dashboard_operations": True,
                    "show_dashboard_debts": True,
                    "dashboard_operations_limit": 8,
                    "scale_percent": 100,
                },
            },
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update(self, user_id: int, preferences_version: int, data: dict) -> UserPreference:
        item = self.get_or_create(user_id)
        item.preferences_version = preferences_version
        item.data = data
        self.db.flush()
        return item
