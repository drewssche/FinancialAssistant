import logging
from datetime import date, datetime, time, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, PlanOperation, PlanOperationEvent, PlanReminderJob, User, UserPreference
from app.services.plan_reminder_service import PlanReminderService


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def test_sync_plan_job_creates_pending_job_for_active_plan():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "plans": {"reminders_enabled": True, "reminder_time": "09:30"},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        db.add(
            PlanOperation(
                id=1,
                user_id=1,
                kind="expense",
                amount="10.00",
                scheduled_date=date(2030, 3, 20),
                note="Будущий план",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.commit()

        plan = db.get(PlanOperation, 1)
        service = PlanReminderService(db)
        service.sync_plan_job(plan)
        db.commit()

        jobs = db.query(PlanReminderJob).all()
        assert len(jobs) == 1
        assert jobs[0].status == "pending"
        scheduled_for = jobs[0].scheduled_for
        assert scheduled_for.date().isoformat() == "2030-03-20"
        assert scheduled_for.minute == 30
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_sync_plan_job_uses_browser_timezone_when_ui_timezone_is_auto():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "plans": {"reminders_enabled": True, "reminder_time": "09:00"},
                    "ui": {"timezone": "auto", "browser_timezone": "Europe/Moscow"},
                },
            )
        )
        db.add(
            PlanOperation(
                id=1,
                user_id=1,
                kind="expense",
                amount="10.00",
                scheduled_date=date(2030, 3, 20),
                note="Будущий план",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.commit()

        plan = db.get(PlanOperation, 1)
        service = PlanReminderService(db)
        service.sync_plan_job(plan)
        db.commit()

        job = db.query(PlanReminderJob).one()
        scheduled_for = job.scheduled_for.replace(tzinfo=timezone.utc) if job.scheduled_for.tzinfo is None else job.scheduled_for.astimezone(timezone.utc)
        assert scheduled_for.hour == 6
        assert scheduled_for.minute == 0
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_list_due_jobs_reads_queue_instead_of_scanning_all_plans():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500", username="tester"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "plans": {"reminders_enabled": True, "reminder_time": "09:00"},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        db.add(
            PlanOperation(
                id=1,
                user_id=1,
                kind="expense",
                amount="10.00",
                scheduled_date=date.today(),
                note="Напомнить",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.add(
            PlanReminderJob(
                plan_id=1,
                user_id=1,
                scheduled_for=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db.commit()

        service = PlanReminderService(db)
        jobs = service.list_due_jobs()
        assert len(jobs) == 1
        assert jobs[0]["chat_id"] == "100500"
        assert jobs[0]["plan"].note == "Напомнить"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_mark_job_sent_writes_event_and_schedules_next_day_for_active_plan():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "plans": {"reminders_enabled": True, "reminder_time": "09:00"},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        db.add(
            PlanOperation(
                id=1,
                user_id=1,
                kind="expense",
                amount="10.00",
                scheduled_date=date.today(),
                note="Напомнить о плане",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.add(
            PlanReminderJob(
                id=1,
                plan_id=1,
                user_id=1,
                scheduled_for=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db.commit()

        plan = db.get(PlanOperation, 1)
        job = db.get(PlanReminderJob, 1)
        service = PlanReminderService(db)
        service.mark_job_sent(
            {
                "job": job,
                "plan": plan,
                "config": {
                    "enabled": True,
                    "timezone": timezone.utc,
                    "time": time(hour=9, minute=0),
                },
            }
        )

        events = db.query(PlanOperationEvent).all()
        jobs = db.query(PlanReminderJob).order_by(PlanReminderJob.id.asc()).all()
        assert len(events) == 1
        assert events[0].event_type == "reminded"
        assert jobs[0].status == "sent"
        assert len(jobs) == 2
        assert jobs[1].status == "pending"
        assert jobs[1].scheduled_for > jobs[0].scheduled_for
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_refresh_due_job_payload_returns_none_for_deleted_plan_job():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500", username="tester"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "plans": {"reminders_enabled": True, "reminder_time": "09:00"},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        db.add(
            PlanOperation(
                id=1,
                user_id=1,
                kind="expense",
                amount="10.00",
                scheduled_date=date.today(),
                note="Напомнить",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.add(
            PlanReminderJob(
                id=1,
                plan_id=1,
                user_id=1,
                scheduled_for=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db.commit()

        service = PlanReminderService(db)
        payload = service.list_due_jobs()[0]

        db.delete(db.get(PlanOperation, 1))
        db.commit()

        assert service.refresh_due_job_payload(payload) is None
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_build_reminder_reply_markup_adds_confirm_button():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        plan = PlanOperation(
            id=7,
            user_id=1,
            kind="expense",
            amount="10.00",
            scheduled_date=date.today(),
            note="Напомнить",
            status="active",
            recurrence_enabled=False,
        )

        markup = PlanReminderService(db).build_reminder_reply_markup({"plan": plan})

        assert markup == {
            "inline_keyboard": [[{"text": "Подтвердить", "callback_data": "planc:7"}]]
        }
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_sync_plan_job_emits_background_event(caplog):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "plans": {"reminders_enabled": True, "reminder_time": "09:30"},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        db.add(
            PlanOperation(
                id=1,
                user_id=1,
                kind="expense",
                amount="10.00",
                scheduled_date=date(2030, 3, 20),
                note="Будущий план",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.commit()

        plan = db.get(PlanOperation, 1)
        service = PlanReminderService(db)
        with caplog.at_level(logging.INFO, logger="financial_assistant.jobs"):
            service.sync_plan_job(plan)

        assert "background_job_event component=plan_reminder event=plan_job_synced" in caplog.text
        assert "plan_id=1" in caplog.text
        assert "user_id=1" in caplog.text
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_mark_job_sent_emits_sent_and_rescheduled_background_events(caplog):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "plans": {"reminders_enabled": True, "reminder_time": "09:00"},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        db.add(
            PlanOperation(
                id=1,
                user_id=1,
                kind="expense",
                amount="10.00",
                scheduled_date=date.today(),
                note="Напомнить о плане",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.add(
            PlanReminderJob(
                id=1,
                plan_id=1,
                user_id=1,
                scheduled_for=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db.commit()

        plan = db.get(PlanOperation, 1)
        job = db.get(PlanReminderJob, 1)
        service = PlanReminderService(db)
        with caplog.at_level(logging.INFO, logger="financial_assistant.jobs"):
            service.mark_job_sent(
                {
                    "job": job,
                    "plan": plan,
                    "config": {
                        "enabled": True,
                        "timezone": timezone.utc,
                        "time": time(hour=9, minute=0),
                    },
                }
            )

        assert "background_job_event component=plan_reminder event=job_sent" in caplog.text
        assert "background_job_event component=plan_reminder event=job_rescheduled" in caplog.text
        assert "plan_id=1" in caplog.text
        assert "user_id=1" in caplog.text
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_sync_plan_job_does_not_reschedule_same_day_after_already_reminded():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "plans": {"reminders_enabled": True, "reminder_time": "09:00"},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        reminded_at = datetime(2030, 3, 20, 9, 0, tzinfo=timezone.utc)
        db.add(
            PlanOperation(
                id=1,
                user_id=1,
                kind="expense",
                amount="10.00",
                scheduled_date=date(2030, 3, 20),
                note="Напомнить о плане",
                status="active",
                recurrence_enabled=False,
                last_reminded_at=reminded_at,
                reminder_sent_count=1,
            )
        )
        db.add(
            PlanReminderJob(
                id=1,
                plan_id=1,
                user_id=1,
                scheduled_for=reminded_at,
                status="sent",
                sent_at=reminded_at,
            )
        )
        db.commit()

        plan = db.get(PlanOperation, 1)
        service = PlanReminderService(db)
        service._now_utc = lambda: datetime(2030, 3, 20, 11, 26, tzinfo=timezone.utc)
        service.sync_plan_job(plan)
        db.commit()

        jobs = db.query(PlanReminderJob).order_by(PlanReminderJob.id.asc()).all()
        assert len(jobs) == 2
        assert jobs[0].status == "sent"
        assert jobs[1].status == "pending"
        assert jobs[1].scheduled_for.date().isoformat() == "2030-03-21"
        assert jobs[1].scheduled_for.hour == 9
        assert jobs[1].scheduled_for.minute == 0
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
