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

    service = TelegramDebtReminderBotService(db_session)
    deliveries = service.list_due_deliveries()

    assert len(deliveries) == 1
    assert deliveries[0].chat_id == "100500"
    assert deliveries[0].debt_id == debt.id
    assert deliveries[0].text.startswith("⏰ Скоро срок долга")
    assert "💸 Вам нужно вернуть" in deliveries[0].text
    assert "Скоро срок долга" in deliveries[0].text
    assert "Контрагент: Мария" in deliveries[0].text
    claimed = service.claim_delivery(deliveries[0])
    assert claimed is not None
    assert db_session.get(DebtReminderJob, claimed.payload["job"].id).status == "sending"
    assert service.claim_delivery(deliveries[0]) is None
    service.release_delivery(claimed)
    assert db_session.get(DebtReminderJob, claimed.payload["job"].id).status == "pending"


def test_claim_due_soon_deliveries_cancels_stale_pending_jobs_after_same_day_send(
    db_session: Session,
    monkeypatch,
):
    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Дима",
        direction="lend",
        principal=Decimal("22.00"),
        start_date=date(2026, 9, 3),
        due_date=date(2026, 9, 5),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.add_all(
        [
            DebtReminderJob(
                user_id=1,
                debt_id=int(debt.id),
                event_type="due_soon",
                scheduled_for=datetime(2026, 9, 4, 9, 1, tzinfo=timezone.utc),
                status="pending",
            ),
            DebtReminderJob(
                user_id=1,
                debt_id=int(debt.id),
                event_type="due_soon",
                scheduled_for=datetime(2026, 9, 4, 10, 28, tzinfo=timezone.utc),
                status="pending",
            ),
        ]
    )
    db_session.commit()
    monkeypatch.setattr(
        "app.services.telegram_debt_reminder_bot_service.DebtReminderService._now_utc",
        lambda self: datetime(2026, 9, 4, 11, 7, tzinfo=timezone.utc),
    )
    service = TelegramDebtReminderBotService(db_session)
    candidates = service.list_due_deliveries()
    assert len(candidates) == 2
    candidate_job_ids = [int(candidate.payload["job"].id) for candidate in candidates]

    db_session.add(
        DebtReminderJob(
            user_id=1,
            debt_id=int(debt.id),
            event_type="due_soon",
            scheduled_for=datetime(2026, 9, 4, 9, 0, tzinfo=timezone.utc),
            status="sent",
            sent_at=datetime(2026, 9, 4, 9, 1, tzinfo=timezone.utc),
        )
    )
    db_session.commit()

    assert [service.claim_delivery(candidate) for candidate in candidates] == [None, None]
    stale_jobs = (
        db_session.query(DebtReminderJob)
        .filter(DebtReminderJob.id.in_(candidate_job_ids))
        .order_by(DebtReminderJob.id.asc())
        .all()
    )
    assert [job.status for job in stale_jobs] == ["canceled", "canceled"]


def test_failed_delivery_release_remains_pending_and_can_be_claimed_again(
    db_session: Session,
    monkeypatch,
):
    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Повторная отправка",
        direction="lend",
        principal=Decimal("22.00"),
        start_date=date(2026, 9, 3),
        due_date=date(2026, 9, 5),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.add(
        DebtReminderJob(
            user_id=1,
            debt_id=int(debt.id),
            event_type="due_soon",
            scheduled_for=datetime(2026, 9, 4, 9, 0, tzinfo=timezone.utc),
            status="pending",
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        "app.services.telegram_debt_reminder_bot_service.DebtReminderService._now_utc",
        lambda self: datetime(2026, 9, 4, 9, 5, tzinfo=timezone.utc),
    )
    service = TelegramDebtReminderBotService(db_session)

    first_candidate = service.list_due_deliveries()[0]
    first_claim = service.claim_delivery(first_candidate)
    assert first_claim is not None
    service.release_delivery(first_claim)

    stored_job = db_session.get(DebtReminderJob, int(first_claim.payload["job"].id))
    assert stored_job is not None
    assert stored_job.status == "pending"
    assert stored_job.sent_at is None
    retry_candidates = service.list_due_deliveries()
    assert len(retry_candidates) == 1
    retry_claim = service.claim_delivery(retry_candidates[0])
    assert retry_claim is not None
    assert retry_claim.payload["job"].id == first_claim.payload["job"].id
    assert db_session.get(DebtReminderJob, int(retry_claim.payload["job"].id)).status == "sending"


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
    assert deliveries[0].text.startswith("⚠️ Срок долга наступил")
    assert "Срок долга наступил" in deliveries[0].text
    assert "Контрагент: Олег" in deliveries[0].text
