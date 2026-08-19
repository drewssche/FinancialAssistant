from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, Operation, PlanOperation, User, UserPreference
from app.repositories.currency_repo import CurrencyRepository
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


def test_confirm_plan_from_telegram_labels_bank_rate_from_bank_perspective(
    db_session: Session,
    monkeypatch,
):
    plan = db_session.get(PlanOperation, 1)
    plan.amount = Decimal("229.00")
    plan.original_amount = Decimal("229.00")
    plan.currency = "EUR"
    plan.base_currency = "BYN"
    plan.fx_rate_source = "bank"
    plan.fx_bank_code = "technobank"
    plan.fx_bank_channel = "cash"
    plan.fx_rate_kind = "sell"
    plan.fx_payment_mode = "direct_conversion"
    db_session.commit()
    now = datetime.now(timezone.utc)
    quote = SimpleNamespace(
        bank_code="technobank",
        bank_name="Технобанк",
        currency="EUR",
        base_currency="BYN",
        scale=1,
        buy_rate=Decimal("3.49"),
        sell_rate=Decimal("3.53"),
        channel="cash",
        location_name="Минск",
        quoted_at=now,
        fetched_at=now,
    )
    monkeypatch.setattr(CurrencyRepository, "get_bank_rate", lambda _repo, **_kwargs: quote)

    result = TelegramPlanBotService(db_session).confirm_plan_from_telegram(
        telegram_id="100500",
        plan_id=1,
    )

    assert "229.00 EUR → 808.37 BYN" in result.message_text
    assert "Технобанк · продажа банком · наличные" in result.message_text
    assert "3.530000 BYN за 1 EUR" in result.message_text


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
