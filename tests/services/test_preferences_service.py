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
                    "debts": {"reminders_enabled": True, "reminder_time": "09:30"},
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
                    "debts": {"reminders_enabled": True, "reminder_time": "10:45"},
                    "ui": {"timezone": "Europe/Minsk"},
                },
            )

        assert updated.preferences_version == 2
        assert "background_job_event component=preferences event=preferences_updated" in caplog.text
        assert "background_job_event component=plan_reminder event=user_jobs_synced" in caplog.text
        assert "background_job_event component=debt_reminder event=user_jobs_synced" in caplog.text
        assert "user_id=1" in caplog.text
        assert "preferences_version=2" in caplog.text
        assert "plan_reminders_enabled=False" in caplog.text
        assert "plan_reminder_time=08:15" in caplog.text
        assert "debt_reminders_enabled=True" in caplog.text
        assert "debt_reminder_time=10:45" in caplog.text
        assert "timezone=Europe/Minsk" in caplog.text
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_update_preferences_preserves_currency_bot_runtime_markers():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "currency": {
                        "tracked_currencies": ["EUR"],
                        "telegram_digest_enabled": True,
                        "last_digest_sent_on": "2026-08-05",
                        "digest_delivery_claimed_on": "2026-08-05",
                        "currency_alerts": {
                            "EUR": {
                                "above_rate": "3.3000",
                                "below_rate": "",
                                "last_above_marker": "active:above:3.300000",
                                "last_below_marker": "",
                            }
                        },
                    }
                },
            )
        )
        db.commit()

        updated = PreferencesService(db).update_preferences(
            user_id=1,
            preferences_version=2,
            data={
                "currency": {
                    "tracked_currencies": ["EUR"],
                    "telegram_digest_enabled": True,
                    "currency_alerts": {
                        "EUR": {
                            "above_rate": "3.3000",
                            "below_rate": "",
                            "last_above_marker": "",
                            "last_below_marker": "",
                        }
                    },
                }
            },
        )

        currency = updated.data["currency"]
        assert currency["last_digest_sent_on"] == "2026-08-05"
        assert currency["digest_delivery_claimed_on"] == "2026-08-05"
        assert currency["currency_alerts"]["EUR"]["last_above_marker"] == "active:above:3.300000"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_update_preferences_resets_alert_marker_when_threshold_changes():
    current = {
        "currency": {
            "currency_alerts": {
                "EUR": {"above_rate": "3.3000", "last_above_marker": "active:above:3.300000"}
            }
        }
    }
    incoming = {
        "currency": {
            "currency_alerts": {
                "EUR": {"above_rate": "3.4000", "last_above_marker": "active:above:3.300000"}
            }
        }
    }

    merged = PreferencesService._preserve_currency_runtime_state(current, incoming)

    assert merged["currency"]["currency_alerts"]["EUR"]["last_above_marker"] == ""
