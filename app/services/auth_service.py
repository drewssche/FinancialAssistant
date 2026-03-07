from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.core.telegram_auth import (
    verify_and_extract_telegram_login_widget_user,
    verify_and_extract_telegram_user,
)
from app.services.telegram_admin_notifier import notify_new_pending_user
from app.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.settings = get_settings()

    def _is_admin_telegram_id(self, telegram_id: str) -> bool:
        return telegram_id in self.settings.admin_telegram_id_set

    def _resolve_new_user_status(self, telegram_id: str) -> str:
        return "approved" if self._is_admin_telegram_id(telegram_id) else "pending"

    def _sync_admin_status(self, user, telegram_id: str) -> None:
        if self._is_admin_telegram_id(telegram_id) and user.status != "approved":
            user.status = "approved"

    def _upsert_telegram_user(self, telegram_user: dict) -> str:
        telegram_id = telegram_user["telegram_id"]
        created = False

        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            created = True
            user = self.user_repo.create_with_telegram_identity(
                telegram_id=telegram_id,
                display_name=telegram_user.get("display_name"),
                username=telegram_user.get("username"),
                avatar_url=telegram_user.get("avatar_url"),
                status=self._resolve_new_user_status(telegram_id),
            )
        self._sync_admin_status(user, telegram_id)

        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        if created and user.status == "pending":
            notify_new_pending_user(
                user_id=user.id,
                display_name=user.display_name,
                username=telegram_user.get("username"),
                telegram_id=telegram_id,
                created_at=user.created_at,
            )
        return create_access_token({"sub": str(user.id)})

    def login_with_telegram(self, init_data: str) -> str:
        telegram_user = verify_and_extract_telegram_user(
            init_data=init_data,
            bot_token=self.settings.telegram_bot_token,
            max_age_seconds=self.settings.telegram_auth_max_age_seconds,
        )
        return self._upsert_telegram_user(telegram_user)

    def login_with_telegram_browser(self, auth_data: dict) -> str:
        telegram_user = verify_and_extract_telegram_login_widget_user(
            auth_data=auth_data,
            bot_token=self.settings.telegram_bot_token,
            max_age_seconds=self.settings.telegram_auth_max_age_seconds,
        )
        return self._upsert_telegram_user(telegram_user)
