import logging
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import PlanOperation, User, UserPreference
from app.services.preferences_service import PreferencesService


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def test_update_preferences_emits_background_event_and_triggers_plan_sync(caplog):
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
                scheduled_date=date(2030, 3, 20),
                note="Будущий план",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.commit()

        service = PreferencesService(db)
        with caplog.at_level(logging.INFO, logger="financial_assistant.jobs"):
            updated = service.update_preferences(
                user_id=1,
                preferences_version=2,
                data={
                    "plans": {"reminders_enabled": False, "reminder_time": "08:15"},
                    "ui": {"timezone": "Europe/Minsk"},
                },
            )

        assert updated.preferences_version == 2
        assert "background_job_event component=preferences event=preferences_updated" in caplog.text
        assert "background_job_event component=plan_reminder event=user_jobs_synced" in caplog.text
        assert "user_id=1" in caplog.text
        assert "preferences_version=2" in caplog.text
        assert "reminders_enabled=False" in caplog.text
        assert "reminder_time=08:15" in caplog.text
        assert "timezone=Europe/Minsk" in caplog.text
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
