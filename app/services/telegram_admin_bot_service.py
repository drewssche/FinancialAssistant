from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import User
from app.repositories.user_repo import UserRepository


class TelegramAdminBotServiceError(Exception):
    pass


class UnknownTelegramAdminActionError(TelegramAdminBotServiceError):
    pass


class TelegramAdminTargetUserNotFoundError(TelegramAdminBotServiceError):
    pass


@dataclass(frozen=True)
class TelegramAdminAccessResult:
    message_text: str
    callback_text: str


def _format_user_label(user: User) -> str:
    identity = next((item for item in (user.identities or []) if item.provider == "telegram"), None)
    username = f"@{identity.username}" if identity and identity.username else "—"
    telegram_id = identity.provider_user_id if identity else "—"
    return (
        f"Имя: {user.display_name or 'Без имени'}\n"
        f"Username: {username}\n"
        f"Telegram ID: {telegram_id}\n"
        f"User ID: {user.id}"
    )


class TelegramAdminBotService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def review_access_request(self, *, action: str, user_id: int) -> TelegramAdminAccessResult:
        if action not in {"approve", "reject"}:
            raise UnknownTelegramAdminActionError("Неизвестное действие")

        user = self.repo.get_by_id(user_id)
        if not user:
            raise TelegramAdminTargetUserNotFoundError("Пользователь не найден")

        next_status = "approved" if action == "approve" else "rejected"
        changed = user.status != next_status
        user.status = next_status
        self.db.commit()
        self.db.refresh(user)

        status_label = "Одобрен" if next_status == "approved" else "Отклонен"
        callback_text = status_label if changed else f"Уже: {status_label.lower()}"
        message_text = f"Заявка обработана: {status_label}\n\n{_format_user_label(user)}"
        return TelegramAdminAccessResult(message_text=message_text, callback_text=callback_text)
