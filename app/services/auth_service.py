from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.core.telegram_auth import verify_and_extract_telegram_user
from app.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.settings = get_settings()

    def login_with_telegram(self, init_data: str) -> str:
        telegram_user = verify_and_extract_telegram_user(
            init_data=init_data,
            bot_token=self.settings.telegram_bot_token,
            max_age_seconds=self.settings.telegram_auth_max_age_seconds,
        )
        telegram_id = telegram_user["telegram_id"]

        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            user = self.user_repo.create_with_telegram_identity(
                telegram_id=telegram_id,
                display_name=telegram_user.get("display_name"),
                username=telegram_user.get("username"),
                avatar_url=telegram_user.get("avatar_url"),
            )

        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        return create_access_token({"sub": str(user.id)})

    def login_dev(
        self,
        telegram_id: int,
        first_name: str,
        username: str,
        avatar_url: str | None = None,
    ) -> str:
        user = self.user_repo.get_by_telegram_id(str(telegram_id))
        if not user:
            user = self.user_repo.create_with_telegram_identity(
                telegram_id=str(telegram_id),
                display_name=first_name,
                username=username,
                avatar_url=avatar_url,
            )

        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        return create_access_token({"sub": str(user.id)})
