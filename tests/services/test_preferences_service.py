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


def test_stale_settings_session_freshly_preserves_manual_digest_marker():
    engine, SessionLocal = _make_session()
    settings_db = SessionLocal()
    delivery_db = SessionLocal()
    verification_db = SessionLocal()
    try:
        settings_db.add(User(id=1, display_name="Tester", status="active"))
        settings_db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "currency": {
                        "tracked_currencies": ["USD"],
                        "telegram_digest_enabled": True,
                    }
                },
            )
        )
        settings_db.commit()

        stale = settings_db.get(UserPreference, 1)
        assert "last_digest_sent_on" not in stale.data["currency"]

        delivered = delivery_db.get(UserPreference, 1)
        latest = dict(delivered.data)
        latest_currency = dict(latest["currency"])
        latest_currency["last_digest_sent_on"] = "2026-08-26"
        latest["currency"] = latest_currency
        delivered.data = latest
        delivery_db.commit()

        updated = PreferencesService(settings_db).update_preferences(
            user_id=1,
            preferences_version=2,
            data={
                "currency": {
                    "tracked_currencies": ["EUR"],
                    "telegram_digest_enabled": True,
                }
            },
        )

        assert updated.data["currency"]["tracked_currencies"] == ["EUR"]
        assert updated.data["currency"]["last_digest_sent_on"] == "2026-08-26"
        verification_db.expire_all()
        persisted = verification_db.get(UserPreference, 1)
        assert persisted.data["currency"]["tracked_currencies"] == ["EUR"]
        assert persisted.data["currency"]["last_digest_sent_on"] == "2026-08-26"
    finally:
        verification_db.close()
        delivery_db.close()
        settings_db.close()
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


def test_update_preferences_preserves_bank_alert_marker_only_for_same_rule():
    current = {
        "currency": {
            "bank_rate_alerts": [
                {
                    "id": "sell-usd",
                    "action": "sell",
                    "currency": "USD",
                    "bank_code": "best",
                    "threshold": "3.1000",
                    "last_marker": "active:sell:3.100000",
                }
            ]
        }
    }
    unchanged = {
        "currency": {
            "bank_rate_alerts": [
                {
                    "id": "sell-usd",
                    "action": "sell",
                    "currency": "USD",
                    "bank_code": "best",
                    "threshold": "3.1000",
                    "last_marker": "",
                }
            ]
        }
    }
    changed = {
        "currency": {
            "bank_rate_alerts": [
                {
                    "id": "sell-usd",
                    "action": "sell",
                    "currency": "USD",
                    "bank_code": "best",
                    "threshold": "3.2000",
                    "last_marker": "active:sell:3.100000",
                }
            ]
        }
    }

    preserved = PreferencesService._preserve_currency_runtime_state(current, unchanged)
    reset = PreferencesService._preserve_currency_runtime_state(current, changed)

    preserved_rule = preserved["currency"]["bank_rate_alerts"][0]
    reset_rule = reset["currency"]["bank_rate_alerts"][0]
    assert preserved_rule["rate_kind"] == "buy"
    assert preserved_rule["above_rate"] == "3.1000"
    assert preserved_rule["last_above_marker"] == "active:above:3.1000"
    assert reset_rule["last_above_marker"] == ""
    assert "action" not in preserved_rule
    assert "threshold" not in preserved_rule
