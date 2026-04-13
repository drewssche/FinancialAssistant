from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, FxRateSnapshot, FxTrade, User, UserPreference
from app.services.telegram_currency_digest_bot_service import TelegramCurrencyDigestBotService


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def test_list_due_deliveries_builds_currency_digest(monkeypatch):
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
                        "telegram_digest_enabled": True,
                        "telegram_digest_time": "00:00",
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.add(
            FxTrade(
                id=1,
                user_id=1,
                side="buy",
                asset_currency="USD",
                quote_currency="BYN",
                quantity=Decimal("100"),
                unit_price=Decimal("3.20"),
                fee=Decimal("2.00"),
                trade_date=date(2026, 3, 1),
            )
        )
        db.add(
            FxRateSnapshot(
                id=1,
                user_id=1,
                currency="USD",
                rate=Decimal("3.25"),
                rate_date=date(2026, 3, 26),
                source="manual",
            )
        )
        db.add(
            FxRateSnapshot(
                id=2,
                user_id=1,
                currency="USD",
                rate=Decimal("3.27"),
                rate_date=date(2026, 3, 27),
                source="manual",
            )
        )
        db.commit()

        monkeypatch.setattr(
            "app.services.telegram_currency_digest_bot_service.CurrencyRateRefreshService.refresh_user_tracked_rates",
            lambda self, user_id, prefs=None: [],
        )

        deliveries = TelegramCurrencyDigestBotService(db).list_due_deliveries()

        assert len(deliveries) == 1
        delivery = deliveries[0]
        assert delivery.chat_id == "100500"
        assert delivery.text.startswith("💱 Курсы")
        assert "📈 USD:" in delivery.text
        assert "USD: курс 3.2700, +0.0200 за день" in delivery.text
        assert "позиция 100.00 USD" in delivery.text
        assert "оценка 327.00 BYN" in delivery.text
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_mark_delivery_sent_persists_last_digest_sent_on(monkeypatch):
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
                        "telegram_digest_enabled": True,
                        "telegram_digest_time": "00:00",
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.commit()

        monkeypatch.setattr(
            "app.services.telegram_currency_digest_bot_service.CurrencyRateRefreshService.refresh_user_tracked_rates",
            lambda self, user_id, prefs=None: [],
        )
        service = TelegramCurrencyDigestBotService(db)
        delivery = service.list_due_deliveries()[0]
        service.mark_delivery_sent(delivery)

        prefs = db.get(UserPreference, 1)
        assert prefs.data["currency"]["last_digest_sent_on"]
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
