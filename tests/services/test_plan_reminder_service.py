from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, PlanOperation, PlanOperationEvent, User, UserPreference
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


def test_collect_due_reminders_skips_items_already_reminded_today():
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
                    "plans": {"reminders_enabled": True},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        db.add(
            PlanOperation(
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
            PlanOperation(
                user_id=1,
                kind="expense",
                amount="11.00",
                scheduled_date=date.today(),
                note="Уже напомнили",
                status="active",
                recurrence_enabled=False,
                last_reminded_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

        service = PlanReminderService(db)
        payloads = service.collect_due_reminders()
        assert len(payloads) == 1
        assert payloads[0]["chat_id"] == "100500"
        assert len(payloads[0]["due_items"]) == 1
        assert payloads[0]["due_items"][0].note == "Напомнить"

        text = service.build_reminder_text(payloads[0])
        assert "Планы к подтверждению" in text
        assert "Напомнить" in text
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_collect_due_reminders_respects_preferences_toggle():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Muted", status="active"))
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="200500", username="muted"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "plans": {"reminders_enabled": False},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        db.add(
            PlanOperation(
                user_id=1,
                kind="expense",
                amount="10.00",
                scheduled_date=date.today(),
                note="Без напоминаний",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.commit()

        service = PlanReminderService(db)
        assert service.collect_due_reminders() == []
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_mark_reminded_items_writes_history_event():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
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
        db.commit()

        plan = db.get(PlanOperation, 1)
        service = PlanReminderService(db)
        service.mark_reminded_items([plan])

        events = db.query(PlanOperationEvent).all()
        assert len(events) == 1
        assert events[0].event_type == "reminded"
        assert events[0].effective_date == date.today()
        assert events[0].note == "Напомнить о плане"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
