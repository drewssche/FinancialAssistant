from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuthIdentity, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_telegram_id(self, telegram_id: str) -> User | None:
        stmt = (
            select(User)
            .join(AuthIdentity, AuthIdentity.user_id == User.id)
            .where(AuthIdentity.provider == "telegram", AuthIdentity.provider_user_id == telegram_id)
        )
        return self.db.scalar(stmt)

    def get_telegram_id_for_user(self, user_id: int) -> str | None:
        stmt = select(AuthIdentity.provider_user_id).where(
            AuthIdentity.user_id == user_id,
            AuthIdentity.provider == "telegram",
        )
        return self.db.scalar(stmt)

    def create_with_telegram_identity(
        self,
        telegram_id: str,
        display_name: str | None,
        username: str | None,
        avatar_url: str | None = None,
        status: str = "pending",
    ) -> User:
        user = User(display_name=display_name, avatar_url=avatar_url, status=status)
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

    def list_users(self, *, status: str | None = None) -> list[User]:
        stmt = select(User).order_by(User.created_at.desc(), User.id.desc())
        if status:
            stmt = stmt.where(User.status == status)
        return list(self.db.scalars(stmt))
