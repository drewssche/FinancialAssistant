from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, DebtReminderJob, User, UserPreference
from app.services.debt_service import DebtService
from app.services.debt_reminder_service import DebtReminderService
from app.services.telegram_debt_reminder_bot_service import TelegramDebtReminderBotService


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
        db.add(User(id=1, display_name="Debt User", status="approved"))
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500", username="debt_user"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={"plans": {"reminders_enabled": True, "reminder_time": "09:00"}, "ui": {"timezone": "UTC"}},
            )
        )
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_list_due_deliveries_builds_due_soon_text(db_session: Session, monkeypatch):
    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Мария",
        direction="borrow",
        principal=Decimal("300.00"),
        start_date=date(2026, 3, 20),
        due_date=date(2026, 3, 24),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.commit()
    reminder_service = DebtReminderService(db_session)
    monkeypatch.setattr(
        reminder_service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 10, 5, tzinfo=timezone.utc),
    )
    reminder_service.sync_debt_job(user_id=1, debt_id=int(debt.id))
    monkeypatch.setattr(
        "app.services.telegram_debt_reminder_bot_service.DebtReminderService._now_utc",
        lambda self: datetime(2026, 3, 23, 10, 7, tzinfo=timezone.utc),
    )

    deliveries = TelegramDebtReminderBotService(db_session).list_due_deliveries()

    assert len(deliveries) == 1
    assert deliveries[0].chat_id == "100500"
    assert deliveries[0].debt_id == debt.id
    assert "Скоро срок долга" in deliveries[0].text
    assert "Контрагент: Мария" in deliveries[0].text


def test_list_due_deliveries_builds_overdue_text(db_session: Session, monkeypatch):
    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Олег",
        direction="borrow",
        principal=Decimal("300.00"),
        start_date=date(2026, 3, 20),
        due_date=date(2026, 3, 22),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.commit()
    reminder_service = DebtReminderService(db_session)
    monkeypatch.setattr(
        reminder_service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 10, 5, tzinfo=timezone.utc),
    )
    reminder_service.sync_debt_job(user_id=1, debt_id=int(debt.id))
    monkeypatch.setattr(
        "app.services.telegram_debt_reminder_bot_service.DebtReminderService._now_utc",
        lambda self: datetime(2026, 3, 23, 10, 7, tzinfo=timezone.utc),
    )

    deliveries = TelegramDebtReminderBotService(db_session).list_due_deliveries()

    assert len(deliveries) == 1
    assert "Срок долга наступил" in deliveries[0].text
    assert "Контрагент: Олег" in deliveries[0].text
