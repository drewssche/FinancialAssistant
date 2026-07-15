from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import ActivityEvent, AuthIdentity, FxRateSnapshot, User, UserPreference
from app.services.telegram_currency_alert_bot_service import TelegramCurrencyAlertBotService


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def test_list_due_deliveries_builds_threshold_alert(monkeypatch):
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
                    "currency": {
                        "tracked_currencies": ["USD"],
                        "currency_alerts": {
                            "USD": {
                                "above_rate": "3.3000",
                            }
                        },
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.add(
            FxRateSnapshot(
                id=1,
                user_id=1,
                currency="USD",
                rate=Decimal("3.4200"),
                rate_date=date(2026, 3, 28),
                source="manual",
            )
        )
        db.commit()

        monkeypatch.setattr(
            "app.services.telegram_currency_alert_bot_service.CurrencyRateRefreshService.refresh_user_tracked_rates",
            lambda self, user_id, prefs=None: [],
        )

        deliveries = TelegramCurrencyAlertBotService(db).list_due_deliveries()

        assert len(deliveries) == 1
        delivery = deliveries[0]
        assert delivery.chat_id == "100500"
        assert delivery.text.startswith("🎯 Сработали алерты")
        assert "📈 USD:" in delivery.text
        assert "USD: курс 3.4200 BYN выше порога 3.3000" in delivery.text
        assert len(delivery.triggers) == 1
        assert delivery.triggers[0].direction == "above"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_mark_delivery_sent_persists_marker_and_prevents_duplicates(monkeypatch):
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
                    "currency": {
                        "tracked_currencies": ["USD"],
                        "currency_alerts": {
                            "USD": {
                                "above_rate": "3.3000",
                            }
                        },
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.add(
            FxRateSnapshot(
                id=1,
                user_id=1,
                currency="USD",
                rate=Decimal("3.4200"),
                rate_date=date(2026, 3, 28),
                source="manual",
            )
        )
        db.commit()

        monkeypatch.setattr(
            "app.services.telegram_currency_alert_bot_service.CurrencyRateRefreshService.refresh_user_tracked_rates",
            lambda self, user_id, prefs=None: [],
        )
        events = []
        monkeypatch.setattr(
            "app.services.telegram_currency_alert_bot_service.log_background_job_event",
            lambda job, event, **fields: events.append((job, event, fields)),
        )

        service = TelegramCurrencyAlertBotService(db)
        delivery = service.list_due_deliveries()[0]
        service.mark_delivery_sent(delivery)

        prefs = db.get(UserPreference, 1)
        assert prefs.data["currency"]["currency_alerts"]["USD"]["last_above_marker"] == "active:above:3.300000"
        activity = db.query(ActivityEvent).filter(ActivityEvent.entity_type == "currency_portfolio").one()
        assert activity.event_type == "telegram_sent"
        assert activity.source == "telegram"
        assert activity.metadata_json["message_type"] == "currency_alert"
        assert activity.metadata_json["direction"] == "above"
        events.clear()
        assert service.list_due_deliveries() == []
        assert events == [
            (
                "currency_alerts",
                "alerts_suppressed",
                {"user_id": 1, "trigger_count": 1, "directions": ["above"]},
            )
        ]
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_list_due_deliveries_collects_above_and_below_alerts_when_both_match(monkeypatch):
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
                    "currency": {
                        "tracked_currencies": ["USD"],
                        "currency_alerts": {
                            "USD": {
                                "above_rate": "3.0000",
                                "below_rate": "4.0000",
                            }
                        },
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.add(
            FxRateSnapshot(
                id=1,
                user_id=1,
                currency="USD",
                rate=Decimal("3.4200"),
                rate_date=date(2026, 3, 28),
                source="manual",
            )
        )
        db.commit()

        monkeypatch.setattr(
            "app.services.telegram_currency_alert_bot_service.CurrencyRateRefreshService.refresh_user_tracked_rates",
            lambda self, user_id, prefs=None: [],
        )

        service = TelegramCurrencyAlertBotService(db)
        delivery = service.list_due_deliveries()[0]

        assert [trigger.direction for trigger in delivery.triggers] == ["above", "below"]
        assert "выше порога 3.0000" in delivery.text
        assert "ниже порога 4.0000" in delivery.text

        service.mark_delivery_sent(delivery)

        prefs = db.get(UserPreference, 1)
        alert_state = prefs.data["currency"]["currency_alerts"]["USD"]
        assert alert_state["last_above_marker"]
        assert alert_state["last_below_marker"]
        activity = db.query(ActivityEvent).filter(ActivityEvent.entity_type == "currency_portfolio").order_by(ActivityEvent.id.asc()).all()
        assert [item.metadata_json["direction"] for item in activity] == ["above", "below"]
        assert service.list_due_deliveries() == []
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_threshold_change_rearms_alert_even_when_rate_marker_was_sent(monkeypatch):
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
                    "currency": {
                        "tracked_currencies": ["USD"],
                        "currency_alerts": {
                            "USD": {
                                "above_rate": "3.3000",
                                "last_above_marker": "2026-03-28:3.420000:above:3.200000",
                            }
                        },
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.add(
            FxRateSnapshot(
                id=1,
                user_id=1,
                currency="USD",
                rate=Decimal("3.4200"),
                rate_date=date(2026, 3, 28),
                source="manual",
            )
        )
        db.commit()

        monkeypatch.setattr(
            "app.services.telegram_currency_alert_bot_service.CurrencyRateRefreshService.refresh_user_tracked_rates",
            lambda self, user_id, prefs=None: [],
        )

        service = TelegramCurrencyAlertBotService(db)
        delivery = service.list_due_deliveries()[0]

        assert len(delivery.triggers) == 1
        assert delivery.triggers[0].direction == "above"
        assert delivery.triggers[0].marker == "active:above:3.300000"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_legacy_marker_with_same_threshold_suppresses_new_rate_snapshot(monkeypatch):
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
                    "currency": {
                        "tracked_currencies": ["USD"],
                        "currency_alerts": {
                            "USD": {
                                "above_rate": "3.3000",
                                "last_above_marker": "2026-03-27:3.410000:above:3.300000",
                            }
                        },
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.add(
            FxRateSnapshot(
                id=1,
                user_id=1,
                currency="USD",
                rate=Decimal("3.4200"),
                rate_date=date(2026, 3, 28),
                source="manual",
            )
        )
        db.commit()
        monkeypatch.setattr(
            "app.services.telegram_currency_alert_bot_service.CurrencyRateRefreshService.refresh_user_tracked_rates",
            lambda self, user_id, prefs=None: [],
        )

        assert TelegramCurrencyAlertBotService(db).list_due_deliveries() == []
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_alert_rearms_only_after_rate_leaves_trigger_zone(monkeypatch):
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
                    "currency": {
                        "tracked_currencies": ["USD"],
                        "currency_alerts": {"USD": {"above_rate": "3.3000"}},
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        snapshot = FxRateSnapshot(
            id=1,
            user_id=1,
            currency="USD",
            rate=Decimal("3.4200"),
            rate_date=date(2026, 3, 28),
            source="manual",
        )
        db.add(snapshot)
        db.commit()
        monkeypatch.setattr(
            "app.services.telegram_currency_alert_bot_service.CurrencyRateRefreshService.refresh_user_tracked_rates",
            lambda self, user_id, prefs=None: [],
        )

        service = TelegramCurrencyAlertBotService(db)
        service.mark_delivery_sent(service.list_due_deliveries()[0])
        assert service.list_due_deliveries() == []

        snapshot.rate = Decimal("3.1000")
        snapshot.rate_date = date(2026, 3, 29)
        db.commit()
        assert service.list_due_deliveries() == []
        prefs = db.get(UserPreference, 1)
        assert prefs.data["currency"]["currency_alerts"]["USD"]["last_above_marker"] == ""

        snapshot.rate = Decimal("3.5000")
        snapshot.rate_date = date(2026, 3, 30)
        db.commit()
        delivery = service.list_due_deliveries()[0]
        assert delivery.triggers[0].marker == "active:above:3.300000"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
