from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import ActivityEvent, AuthIdentity, DebtReminderJob, User, UserPreference
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


def _set_user_timezone(db_session: Session, timezone_name: str) -> None:
    preference = db_session.scalar(select(UserPreference).where(UserPreference.user_id == 1))
    assert preference is not None
    data = dict(preference.data)
    data["ui"] = {**(data.get("ui") or {}), "timezone": timezone_name}
    preference.data = data
    db_session.commit()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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
    activity = db_session.query(ActivityEvent).filter(ActivityEvent.entity_type == "debt", ActivityEvent.entity_id == debt.id).order_by(ActivityEvent.id.desc()).first()
    assert activity is not None
    assert activity.event_type == "telegram_sent"
    assert activity.source == "telegram"
    assert activity.metadata_json["message_type"] == "debt_reminder"


def test_due_soon_reminder_is_not_scheduled_again_by_same_day_user_sync(db_session: Session, monkeypatch):
    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Дима",
        direction="lend",
        principal=Decimal("22.00"),
        start_date=date(2026, 9, 3),
        due_date=date(2026, 9, 5),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.commit()
    service = DebtReminderService(db_session)
    current_now = {"value": datetime(2026, 9, 4, 9, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(service, "_now_utc", lambda: current_now["value"])

    service.sync_user_jobs(user_id=1)
    current_now["value"] = datetime(2026, 9, 4, 9, 2, tzinfo=timezone.utc)
    due_jobs = service.list_due_jobs()
    assert len(due_jobs) == 1

    service.mark_job_sent(due_jobs[0])
    current_now["value"] = datetime(2026, 9, 4, 10, 28, tzinfo=timezone.utc)
    service.sync_user_jobs(user_id=1)
    current_now["value"] = datetime(2026, 9, 4, 10, 33, tzinfo=timezone.utc)
    service.sync_user_jobs(user_id=1)

    jobs = list(
        db_session.scalars(
            select(DebtReminderJob)
            .where(DebtReminderJob.debt_id == debt.id)
            .order_by(DebtReminderJob.id.asc())
        )
    )
    assert [job.status for job in jobs].count("sent") == 1
    assert [job for job in jobs if job.status == "pending"] == []
    assert service.list_due_jobs() == []


def test_sent_today_does_not_suppress_due_soon_job_for_future_local_day(db_session: Session, monkeypatch):
    _set_user_timezone(db_session, "Europe/Minsk")
    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Будущий срок",
        direction="lend",
        principal=Decimal("22.00"),
        start_date=date(2026, 9, 3),
        due_date=date(2026, 9, 5),
    )
    db_session.query(DebtReminderJob).delete()
    debt.due_date = date(2026, 9, 7)
    db_session.add(
        DebtReminderJob(
            user_id=1,
            debt_id=int(debt.id),
            event_type="due_soon",
            scheduled_for=datetime(2026, 9, 4, 6, 0, tzinfo=timezone.utc),
            status="sent",
            sent_at=datetime(2026, 9, 4, 6, 2, tzinfo=timezone.utc),
        )
    )
    db_session.commit()
    service = DebtReminderService(db_session)
    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 9, 4, 8, 0, tzinfo=timezone.utc),
    )

    service.sync_debt_job(user_id=1, debt_id=int(debt.id))

    pending = db_session.scalar(
        select(DebtReminderJob).where(
            DebtReminderJob.debt_id == debt.id,
            DebtReminderJob.event_type == "due_soon",
            DebtReminderJob.status == "pending",
        )
    )
    assert pending is not None
    scheduled_local = _as_utc(pending.scheduled_for).astimezone(ZoneInfo("Europe/Minsk"))
    assert scheduled_local == datetime(2026, 9, 6, 9, 0, tzinfo=ZoneInfo("Europe/Minsk"))


def test_due_soon_sent_today_moves_new_overdue_job_to_next_local_day(db_session: Session, monkeypatch):
    _set_user_timezone(db_session, "Europe/Minsk")
    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Просроченный срок",
        direction="lend",
        principal=Decimal("22.00"),
        start_date=date(2026, 9, 1),
        due_date=date(2026, 9, 5),
    )
    db_session.query(DebtReminderJob).delete()
    debt.due_date = date(2026, 9, 3)
    db_session.add(
        DebtReminderJob(
            user_id=1,
            debt_id=int(debt.id),
            event_type="due_soon",
            scheduled_for=datetime(2026, 9, 4, 6, 0, tzinfo=timezone.utc),
            status="sent",
            sent_at=datetime(2026, 9, 4, 6, 2, tzinfo=timezone.utc),
        )
    )
    db_session.commit()
    service = DebtReminderService(db_session)
    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 9, 4, 8, 0, tzinfo=timezone.utc),
    )

    service.sync_debt_job(user_id=1, debt_id=int(debt.id))

    pending = db_session.scalar(
        select(DebtReminderJob).where(
            DebtReminderJob.debt_id == debt.id,
            DebtReminderJob.event_type == "overdue",
            DebtReminderJob.status == "pending",
        )
    )
    assert pending is not None
    scheduled_local = _as_utc(pending.scheduled_for).astimezone(ZoneInfo("Europe/Minsk"))
    assert scheduled_local == datetime(2026, 9, 5, 9, 0, tzinfo=ZoneInfo("Europe/Minsk"))


def test_overdue_daily_limit_uses_europe_minsk_local_midnight(db_session: Session, monkeypatch):
    _set_user_timezone(db_session, "Europe/Minsk")
    debt, _ = DebtService(db_session).create_debt(
        user_id=1,
        counterparty="Полуночный срок",
        direction="lend",
        principal=Decimal("22.00"),
        start_date=date(2026, 9, 1),
        due_date=date(2026, 9, 3),
    )
    db_session.query(DebtReminderJob).delete()
    db_session.add(
        DebtReminderJob(
            user_id=1,
            debt_id=int(debt.id),
            event_type="overdue",
            scheduled_for=datetime(2026, 9, 4, 20, 58, tzinfo=timezone.utc),
            status="sent",
            sent_at=datetime(2026, 9, 4, 20, 59, tzinfo=timezone.utc),
        )
    )
    db_session.commit()
    service = DebtReminderService(db_session)
    monkeypatch.setattr(
        service,
        "_now_utc",
        lambda: datetime(2026, 9, 4, 21, 1, tzinfo=timezone.utc),
    )

    service.sync_debt_job(user_id=1, debt_id=int(debt.id))

    pending = db_session.scalar(
        select(DebtReminderJob).where(
            DebtReminderJob.debt_id == debt.id,
            DebtReminderJob.event_type == "overdue",
            DebtReminderJob.status == "pending",
        )
    )
    assert pending is not None
    scheduled_local = _as_utc(pending.scheduled_for).astimezone(ZoneInfo("Europe/Minsk"))
    assert scheduled_local == datetime(2026, 9, 5, 9, 0, tzinfo=ZoneInfo("Europe/Minsk"))


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
