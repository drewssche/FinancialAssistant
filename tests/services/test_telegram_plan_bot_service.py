from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, Operation, PlanOperation, User, UserPreference
from app.services.telegram_plan_bot_service import (
    TelegramPlanAlreadyCompletedError,
    TelegramPlanBotService,
    TelegramPlanNotFoundError,
    TelegramPlanUserNotFoundError,
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
        db.add(User(id=1, display_name="Plan User", status="approved"))
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500", username="plan_user"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={"plans": {"reminders_enabled": True, "reminder_time": "09:00"}, "ui": {"timezone": "UTC"}},
            )
        )
        db.add(
            PlanOperation(
                id=1,
                user_id=1,
                kind="expense",
                amount=Decimal("12.50"),
                scheduled_date=date(2026, 3, 22),
                note="Купить кофе",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_confirm_plan_from_telegram_confirms_operation(db_session: Session):
    result = TelegramPlanBotService(db_session).confirm_plan_from_telegram(telegram_id="100500", plan_id=1)

    assert result.callback_text == "Подтверждено"
    assert "План подтвержден" in result.message_text
    assert "Купить кофе" in result.message_text
    operations = db_session.query(Operation).all()
    assert len(operations) == 1


def test_confirm_plan_from_telegram_rejects_missing_plan(db_session: Session):
    with pytest.raises(TelegramPlanNotFoundError, match="План не найден"):
        TelegramPlanBotService(db_session).confirm_plan_from_telegram(telegram_id="100500", plan_id=999)


def test_confirm_plan_from_telegram_rejects_already_completed_plan(db_session: Session):
    service = TelegramPlanBotService(db_session)
    service.confirm_plan_from_telegram(telegram_id="100500", plan_id=1)

    with pytest.raises(TelegramPlanAlreadyCompletedError, match="План уже обработан"):
        service.confirm_plan_from_telegram(telegram_id="100500", plan_id=1)


def test_confirm_plan_from_telegram_emits_observability_events_on_success(db_session: Session, caplog: pytest.LogCaptureFixture):
    caplog.set_level("INFO")

    TelegramPlanBotService(db_session).confirm_plan_from_telegram(telegram_id="100500", plan_id=1)

    text = caplog.text
    assert "telegram_plan_event event=confirm_attempted" in text
    assert "telegram_id=100500" in text
    assert "plan_id=1" in text
    assert "telegram_plan_event event=confirm_succeeded" in text
    assert "user_id=1" in text


def test_confirm_plan_from_telegram_emits_observability_events_when_user_missing(
    db_session: Session, caplog: pytest.LogCaptureFixture
):
    caplog.set_level("INFO")

    with pytest.raises(TelegramPlanUserNotFoundError, match="Пользователь не найден"):
        TelegramPlanBotService(db_session).confirm_plan_from_telegram(telegram_id="999999", plan_id=1)

    text = caplog.text
    assert "telegram_plan_event event=confirm_attempted" in text
    assert "telegram_plan_event event=user_not_found" in text
    assert "telegram_id=999999" in text


def test_confirm_plan_from_telegram_emits_observability_events_when_plan_missing(
    db_session: Session, caplog: pytest.LogCaptureFixture
):
    caplog.set_level("INFO")

    with pytest.raises(TelegramPlanNotFoundError, match="План не найден"):
        TelegramPlanBotService(db_session).confirm_plan_from_telegram(telegram_id="100500", plan_id=999)

    text = caplog.text
    assert "telegram_plan_event event=confirm_attempted" in text
    assert "telegram_plan_event event=plan_not_found" in text
    assert "telegram_id=100500" in text
    assert "user_id=1" in text
    assert "plan_id=999" in text


def test_confirm_plan_from_telegram_emits_observability_events_when_already_completed(
    db_session: Session, caplog: pytest.LogCaptureFixture
):
    caplog.set_level("INFO")
    service = TelegramPlanBotService(db_session)
    service.confirm_plan_from_telegram(telegram_id="100500", plan_id=1)
    caplog.clear()

    with pytest.raises(TelegramPlanAlreadyCompletedError, match="План уже обработан"):
        service.confirm_plan_from_telegram(telegram_id="100500", plan_id=1)

    text = caplog.text
    assert "telegram_plan_event event=confirm_attempted" in text
    assert "telegram_plan_event event=already_completed" in text
    assert "telegram_id=100500" in text
    assert "user_id=1" in text
