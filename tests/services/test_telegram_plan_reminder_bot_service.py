from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, PlanOperation, PlanReminderJob, User, UserPreference
from app.services.telegram_plan_reminder_bot_service import TelegramPlanReminderBotService


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def test_list_due_deliveries_builds_ready_to_send_payload():
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

        deliveries = TelegramPlanReminderBotService(db).list_due_deliveries()

        assert len(deliveries) == 1
        delivery = deliveries[0]
        assert delivery.chat_id == "100500"
        assert delivery.text.startswith("🧾 План к подтверждению")
        assert "💸 Расход 10.00" in delivery.text
        assert "План к подтверждению" in delivery.text
        assert delivery.reply_markup == {
            "inline_keyboard": [[{"text": "Подтвердить", "callback_data": "planc:1"}]]
        }
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_mark_delivery_sent_delegates_to_plan_reminder_service():
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

        service = TelegramPlanReminderBotService(db)
        delivery = service.list_due_deliveries()[0]
        service.mark_delivery_sent(delivery)

        jobs = db.query(PlanReminderJob).order_by(PlanReminderJob.id.asc()).all()
        assert jobs[0].status == "sent"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
