from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, DebtReminderJob, User, UserPreference
from app.services.debt_service import DebtService
from app.services.debt_reminder_service import DebtReminderService


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
                data={
                    "plans": {"reminders_enabled": True, "reminder_time": "09:00"},
                    "debts": {"reminders_enabled": True, "reminder_time": "09:00"},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_sync_due_soon_job_creates_single_pending_job(db_session: Session, monkeypatch):
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
    service = DebtReminderService(db_session)
    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 10, 15, tzinfo=timezone.utc),
    )

    service.sync_debt_job(user_id=1, debt_id=int(debt.id))
    service.sync_debt_job(user_id=1, debt_id=int(debt.id))

    jobs = list(db_session.scalars(select(DebtReminderJob).order_by(DebtReminderJob.id.asc())))
    assert len(jobs) == 2
    assert jobs[0].status == "canceled"
    assert jobs[1].status == "pending"
    assert jobs[1].event_type == "due_soon"


def test_list_due_jobs_and_mark_sent(db_session: Session, monkeypatch):
    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Иван",
        direction="lend",
        principal=Decimal("150.00"),
        start_date=date(2026, 3, 20),
        due_date=date(2026, 3, 24),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.commit()
    service = DebtReminderService(db_session)
    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 10, 5, tzinfo=timezone.utc),
    )
    service.sync_debt_job(user_id=1, debt_id=int(debt.id))

    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 10, 7, tzinfo=timezone.utc),
    )
    jobs = service.list_due_jobs()

    assert len(jobs) == 1
    assert jobs[0]["chat_id"] == "100500"
    assert jobs[0]["debt"].id == debt.id

    service.mark_job_sent(jobs[0])
    stored_job = db_session.scalar(select(DebtReminderJob).where(DebtReminderJob.debt_id == debt.id))
    assert stored_job is not None
    assert stored_job.status == "sent"


def test_sync_due_soon_job_skips_same_day_debt(db_session: Session, monkeypatch):
    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Павел",
        direction="borrow",
        principal=Decimal("90.00"),
        start_date=date(2026, 3, 20),
        due_date=date(2026, 3, 23),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.commit()
    service = DebtReminderService(db_session)
    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
    )

    service.sync_debt_job(user_id=1, debt_id=int(debt.id))

    jobs = list(db_session.scalars(select(DebtReminderJob)))
    assert jobs == []


def test_sync_overdue_job_uses_daily_dedupe_and_next_day_reschedule(db_session: Session, monkeypatch):
    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Олег",
        direction="borrow",
        principal=Decimal("400.00"),
        start_date=date(2026, 3, 18),
        due_date=date(2026, 3, 22),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.commit()
    service = DebtReminderService(db_session)
    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
    )

    service.sync_debt_job(user_id=1, debt_id=int(debt.id))
    jobs = list(db_session.scalars(select(DebtReminderJob).order_by(DebtReminderJob.id.asc())))
    assert len(jobs) == 1
    assert jobs[0].event_type == "overdue"
    assert jobs[0].status == "pending"

    service.mark_job_sent({"job": jobs[0]})
    jobs = list(db_session.scalars(select(DebtReminderJob).order_by(DebtReminderJob.id.asc())))
    assert len(jobs) == 2
    assert jobs[0].status == "sent"
    assert jobs[1].event_type == "overdue"
    assert jobs[1].status == "pending"
    assert jobs[1].scheduled_for.date().isoformat() == "2026-03-24"

    service.sync_debt_job(user_id=1, debt_id=int(debt.id))
    jobs = list(db_session.scalars(select(DebtReminderJob).order_by(DebtReminderJob.id.asc())))
    assert jobs[-1].event_type == "overdue"
    assert jobs[-1].status == "pending"
    assert jobs[-1].scheduled_for.date().isoformat() == "2026-03-24"


def test_overdue_delivery_uses_current_outstanding_total_after_partial_repayment(db_session: Session, monkeypatch):
    debt_service = DebtService(db_session)
    monkeypatch.setattr(
        debt_service.debt_reminder_service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
    )
    debt, _ = debt_service.create_debt(
        user_id=1,
        counterparty="Нина",
        direction="lend",
        principal=Decimal("500.00"),
        start_date=date(2026, 3, 18),
        due_date=date(2026, 3, 22),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.commit()
    service = DebtReminderService(db_session)
    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
    )
    service.sync_debt_job(user_id=1, debt_id=int(debt.id))
    debt_service.add_repayment(
        user_id=1,
        debt_id=int(debt.id),
        amount=Decimal("200.00"),
        repayment_date=date(2026, 3, 23),
    )
    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 12, 2, tzinfo=timezone.utc),
    )

    jobs = service.list_due_jobs()
    overdue_job = next(item for item in jobs if item["event_type"] == "overdue")
    assert overdue_job["outstanding_total"] == Decimal("300.00")


def test_sync_debt_job_cancels_overdue_jobs_when_due_date_moves_to_future(db_session: Session, monkeypatch):
    debt_service = DebtService(db_session)
    monkeypatch.setattr(
        debt_service.debt_reminder_service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
    )
    debt, _ = debt_service.create_debt(
        user_id=1,
        counterparty="Анна",
        direction="borrow",
        principal=Decimal("120.00"),
        start_date=date(2026, 3, 18),
        due_date=date(2026, 3, 22),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.commit()
    service = DebtReminderService(db_session)
    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
    )
    service.sync_debt_job(user_id=1, debt_id=int(debt.id))

    debt_service.update_debt(
        user_id=1,
        debt_id=int(debt.id),
        updates={"due_date": date(2026, 3, 30)},
    )

    jobs = list(db_session.scalars(select(DebtReminderJob).order_by(DebtReminderJob.id.asc())))
    assert any(job.event_type == "overdue" and job.status == "canceled" for job in jobs)
    assert any(job.event_type == "due_soon" and job.status == "pending" for job in jobs)


def test_debt_reminder_service_falls_back_to_legacy_plan_preferences(db_session: Session, monkeypatch):
    preference = db_session.scalar(select(UserPreference).where(UserPreference.user_id == 1))
    preference.data = {
        "plans": {"reminders_enabled": False, "reminder_time": "08:15"},
        "ui": {"timezone": "UTC"},
    }
    db_session.commit()

    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Легаси",
        direction="borrow",
        principal=Decimal("50.00"),
        start_date=date(2026, 3, 20),
        due_date=date(2026, 3, 24),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.commit()
    service = DebtReminderService(db_session)
    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
    )

    service.sync_debt_job(user_id=1, debt_id=int(debt.id))

    jobs = list(db_session.scalars(select(DebtReminderJob)))
    assert jobs == []
