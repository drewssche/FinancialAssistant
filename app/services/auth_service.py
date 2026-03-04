from datetime import datetime, timezone
from urllib.parse import parse_qs

from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def login_with_telegram(self, init_data: str) -> str:
        # NOTE: For MVP scaffold we parse initData. Production must verify Telegram hash signature.
        payload = parse_qs(init_data, keep_blank_values=True)
        telegram_id = self._extract_value(payload, "id", "user[id]")
        if not telegram_id:
            raise ValueError("Invalid Telegram payload: missing id")

        display_name = self._extract_value(payload, "first_name", "user[first_name]")
        username = self._extract_value(payload, "username", "user[username]")

        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            user = self.user_repo.create_with_telegram_identity(
                telegram_id=telegram_id,
                display_name=display_name,
                username=username,
            )
        else:
            user.last_login_at = datetime.now(timezone.utc)

        self.db.commit()
        return create_access_token({"sub": str(user.id)})

    @staticmethod
    def _extract_value(payload: dict[str, list[str]], *keys: str) -> str | None:
        for key in keys:
            values = payload.get(key)
            if values and values[0]:
                return values[0]
        return None
