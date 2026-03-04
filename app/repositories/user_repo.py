from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuthIdentity, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_telegram_id(self, telegram_id: str) -> User | None:
        stmt = (
            select(User)
            .join(AuthIdentity, AuthIdentity.user_id == User.id)
            .where(AuthIdentity.provider == "telegram", AuthIdentity.provider_user_id == telegram_id)
        )
        return self.db.scalar(stmt)

    def create_with_telegram_identity(
        self,
        telegram_id: str,
        display_name: str | None,
        username: str | None,
        avatar_url: str | None = None,
    ) -> User:
        user = User(display_name=display_name, avatar_url=avatar_url)
        self.db.add(user)
        self.db.flush()

        identity = AuthIdentity(
            user_id=user.id,
            provider="telegram",
            provider_user_id=telegram_id,
            username=username,
        )
        self.db.add(identity)
        self.db.flush()
        return user
