from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import ActivityEvent, AuthIdentity, FxBankRate, FxRateSnapshot, User, UserPreference
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


def test_legacy_user_sell_alert_becomes_bank_buy_above_alert(monkeypatch):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "currency": {
                        "tracked_currencies": ["USD"],
                        "bank_rate_banks": ["priorbank", "technobank"],
                        "bank_rate_alerts": [
                            {
                                "id": "sell-usd",
                                "action": "sell",
                                "currency": "USD",
                                "bank_code": "best",
                                "threshold": "3.0500",
                            }
                        ],
                    },
                    "ui": {"currency": "BYN"},
                },
            )
        )
        now = datetime.now(timezone.utc)
        db.add_all(
            [
                FxBankRate(
                    bank_code="priorbank",
                    bank_name="Приорбанк",
                    currency="USD",
                    base_currency="BYN",
                    scale=1,
                    buy_rate=Decimal("3.0600"),
                    sell_rate=Decimal("3.1100"),
                    channel="online",
                    fetched_at=now,
                ),
                FxBankRate(
                    bank_code="technobank",
                    bank_name="Технобанк",
                    currency="USD",
                    base_currency="BYN",
                    scale=1,
                    buy_rate=Decimal("3.0800"),
                    sell_rate=Decimal("3.1200"),
                    channel="cash",
                    fetched_at=now,
                ),
            ]
        )
        db.commit()
        monkeypatch.setattr(
            "app.services.telegram_currency_alert_bot_service.BankCurrencyRateRefreshService.refresh_user_selected_rates",
            lambda self, user_id, prefs=None: [],
        )

        service = TelegramCurrencyAlertBotService(db)
        delivery = service.list_due_deliveries()[0]

        assert delivery.triggers == []
        assert len(delivery.bank_triggers) == 1
        assert delivery.bank_triggers[0].bank_code == "technobank"
        assert delivery.bank_triggers[0].rate_kind == "buy"
        assert delivery.bank_triggers[0].direction == "above"
        assert "курс покупки банка 3.0800 BYN в Технобанк" in delivery.text

        service.mark_delivery_sent(delivery)
        prefs = db.get(UserPreference, 1)
        rule = prefs.data["currency"]["bank_rate_alerts"][0]
        assert rule["last_above_marker"] == "active:above:3.050000"
        assert service.list_due_deliveries() == []
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_official_rub_alert_threshold_is_compared_per_100_rub():
    service = TelegramCurrencyAlertBotService.__new__(TelegramCurrencyAlertBotService)

    triggers, _, _ = service._collect_triggers(
        current_rates={"RUB": {"rate": "0.035600", "rate_date": "2026-08-18"}},
        config={
            "alerts": {
                "RUB": {
                    "above_rate": Decimal("3.550000"),
                    "below_rate": None,
                    "last_above_marker": "",
                    "last_below_marker": "",
                }
            }
        },
    )

    assert len(triggers) == 1
    assert triggers[0].current_rate == Decimal("3.560000")


def test_bank_sale_rule_supports_above_and_below_thresholds():
    service = TelegramCurrencyAlertBotService.__new__(TelegramCurrencyAlertBotService)
    bank_rates = [
        {
            "bank_code": "priorbank",
            "bank_name": "Приорбанк",
            "currency": "EUR",
            "buy_rate": Decimal("3.4800"),
            "sell_rate": Decimal("3.5200"),
            "stale": False,
        }
    ]
    config = {
        "bank_alerts": [
            {
                "id": "sale-eur",
                "currency": "EUR",
                "rate_kind": "sell",
                "bank_code": "priorbank",
                "above_rate": Decimal("3.5000"),
                "below_rate": Decimal("3.6000"),
                "last_above_marker": "",
                "last_below_marker": "",
            }
        ]
    }

    triggers, _, _ = service._collect_bank_triggers(bank_rates=bank_rates, config=config)

    assert [trigger.direction for trigger in triggers] == ["above", "below"]
    assert all(trigger.rate_kind == "sell" for trigger in triggers)
    assert all(trigger.current_rate == Decimal("3.5200") for trigger in triggers)


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
