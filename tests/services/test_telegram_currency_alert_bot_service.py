from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, FxRateSnapshot, User, UserPreference
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

        service = TelegramCurrencyAlertBotService(db)
        delivery = service.list_due_deliveries()[0]
        service.mark_delivery_sent(delivery)

        prefs = db.get(UserPreference, 1)
        assert prefs.data["currency"]["currency_alerts"]["USD"]["last_above_marker"]
        assert service.list_due_deliveries() == []
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
