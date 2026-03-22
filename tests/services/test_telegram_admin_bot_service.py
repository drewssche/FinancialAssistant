from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, User
from app.services.telegram_admin_bot_service import (
    TelegramAdminBotService,
    TelegramAdminTargetUserNotFoundError,
    UnknownTelegramAdminActionError,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        pending = User(id=1, display_name="Pending User", status="pending", created_at=datetime.now(timezone.utc))
        rejected = User(id=2, display_name="Rejected User", status="rejected", created_at=datetime.now(timezone.utc))
        db.add_all([pending, rejected])
        db.flush()
        db.add_all(
            [
                AuthIdentity(user_id=1, provider="telegram", provider_user_id="101", username="pending"),
                AuthIdentity(user_id=2, provider="telegram", provider_user_id="202", username="rejected"),
            ]
        )
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_review_access_request_approves_and_formats_message(db_session: Session):
    result = TelegramAdminBotService(db_session).review_access_request(action="approve", user_id=1)

    assert result.callback_text == "Одобрен"
    assert "Заявка обработана: Одобрен" in result.message_text
    assert "@pending" in result.message_text
    user = db_session.scalar(select(User).where(User.id == 1))
    assert user is not None
    assert user.status == "approved"


def test_review_access_request_reports_already_processed_status(db_session: Session):
    result = TelegramAdminBotService(db_session).review_access_request(action="reject", user_id=2)

    assert result.callback_text == "Уже: отклонен"
    assert "Заявка обработана: Отклонен" in result.message_text


def test_review_access_request_rejects_unknown_action(db_session: Session):
    with pytest.raises(UnknownTelegramAdminActionError, match="Неизвестное действие"):
        TelegramAdminBotService(db_session).review_access_request(action="noop", user_id=1)


def test_review_access_request_rejects_missing_user(db_session: Session):
    with pytest.raises(TelegramAdminTargetUserNotFoundError, match="Пользователь не найден"):
        TelegramAdminBotService(db_session).review_access_request(action="approve", user_id=999)
