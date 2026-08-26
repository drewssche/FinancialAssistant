from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import ActivityEvent, AuthIdentity, FxRateSnapshot, FxTrade, User, UserPreference
from app.services.telegram_currency_digest_bot_service import TelegramCurrencyDigestBotService


@pytest.fixture(autouse=True)
def _disable_bank_rate_network(monkeypatch):
    monkeypatch.setattr(
        "app.services.telegram_currency_digest_bot_service.BankCurrencyRateRefreshService.refresh_user_selected_rates",
        lambda self, user_id, prefs=None: [],
    )


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
                        "telegram_digest_chart_enabled": False,
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
        monkeypatch.setattr(
            "app.services.telegram_currency_digest_bot_service.BankCurrencyRateRefreshService.refresh_user_selected_rates",
            lambda self, user_id, prefs=None: [],
        )

        deliveries = TelegramCurrencyDigestBotService(db).list_due_deliveries()

        assert len(deliveries) == 1
        delivery = deliveries[0]
        assert delivery.chat_id == "100500"
        assert delivery.text.startswith("💱 Курсы")
        assert "📈 USD:" in delivery.text
        assert "USD: курс НБРБ 3.2700, +0.0200 за день" in delivery.text
        assert "позиция 100.00 USD" in delivery.text
        assert "оценка 327.00 BYN" in delivery.text
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_digest_bank_rates_are_labeled_from_the_bank_perspective():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        service = TelegramCurrencyDigestBotService(db)
        text = service.build_digest_text(
            overview={
                "base_currency": "BYN",
                "current_rates": [],
                "positions": [],
                "bank_rates": [
                    {
                        "currency": "USD",
                        "bank_name": "Приорбанк",
                        "buy_rate": "3.0200",
                        "sell_rate": "3.0500",
                        "stale": False,
                    },
                    {
                        "currency": "USD",
                        "bank_name": "Технобанк",
                        "buy_rate": "3.0100",
                        "sell_rate": "3.0400",
                        "stale": False,
                    },
                ],
                "total_current_value": "0",
                "total_result_value": "0",
            },
            config={"tracked_currencies": ["USD"]},
        )

        assert "🏦 Банки: покупка 3.0200 в Приорбанк; продажа 3.0400 в Технобанк" in text
        assert "Банки: продать" not in text
        assert "; купить" not in text
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
                        "telegram_digest_chart_enabled": False,
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
        service.mark_delivery_sent(delivery, delivery_format="photo")

        prefs = db.get(UserPreference, 1)
        assert prefs.data["currency"]["last_digest_sent_on"]
        activity = db.query(ActivityEvent).filter(ActivityEvent.entity_type == "currency_portfolio").one()
        assert activity.event_type == "telegram_sent"
        assert activity.source == "telegram"
        assert activity.metadata_json["message_type"] == "currency_digest"
        assert activity.metadata_json["tracked_currencies"] == ["USD"]
        assert activity.metadata_json["delivery_format"] == "photo"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_digest_claim_is_persisted_before_send_and_release_allows_retry(monkeypatch):
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
                        "telegram_digest_chart_enabled": False,
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
        assert service.claim_delivery(delivery) is True
        assert TelegramCurrencyDigestBotService(db).list_due_deliveries() == []

        service.release_delivery(delivery)
        retry = TelegramCurrencyDigestBotService(db).list_due_deliveries()
        assert len(retry) == 1
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_due_delivery_attaches_rendered_chart_and_caption(monkeypatch):
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
                        "telegram_digest_chart_enabled": True,
                        "bank_rate_banks": ["priorbank"],
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.commit()

        service = TelegramCurrencyDigestBotService(db)
        monkeypatch.setattr(service.refresh_service, "refresh_user_tracked_rates", lambda **kwargs: [])
        monkeypatch.setattr(service.bank_refresh_service, "refresh_user_selected_rates", lambda **kwargs: [])
        monkeypatch.setattr(
            service.currency_service,
            "get_overview",
            lambda **kwargs: {
                "base_currency": "BYN",
                "current_rates": [
                    {"currency": "USD", "rate": "3.20", "change_value": "0.01"},
                ],
                "positions": [],
                "bank_rates": [],
                "total_current_value": "0",
                "total_result_value": "0",
            },
        )
        chart_calls = []
        monkeypatch.setattr(
            service.chart_data_service,
            "build_payload",
            lambda **kwargs: chart_calls.append(kwargs) or object(),
        )

        class _Renderer:
            def render(self, payload):  # noqa: ANN001
                assert payload is not None
                return b"\x89PNG\r\n\x1a\nchart"

        service.chart_renderer = _Renderer()

        delivery = service.list_due_deliveries()[0]

        assert delivery.photo_png == b"\x89PNG\r\n\x1a\nchart"
        assert delivery.photo_caption == delivery.text
        assert chart_calls[0]["user_id"] == 1
        assert chart_calls[0]["tracked_currencies"] == ["USD"]
        assert chart_calls[0]["bank_codes"] == ["priorbank"]
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_chart_render_failure_keeps_text_digest_available(monkeypatch):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        service = TelegramCurrencyDigestBotService(db)

        def _fail(**kwargs):  # noqa: ANN003
            raise RuntimeError("renderer unavailable")

        monkeypatch.setattr(service.chart_data_service, "build_payload", _fail)
        photo = service._build_chart_png(
            user_id=1,
            overview={},
            config={
                "chart_enabled": True,
                "timezone": service._get_digest_config({"ui": {"timezone": "UTC"}})["timezone"],
                "tracked_currencies": ["USD"],
                "bank_rate_banks": [],
            },
        )

        assert photo is None
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_chart_preference_defaults_on_and_photo_caption_stays_within_telegram_limit():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        service = TelegramCurrencyDigestBotService(db)

        assert service._get_digest_config({"currency": {}})["chart_enabled"] is True
        assert service._get_digest_config(
            {"currency": {"telegram_digest_chart_enabled": False}}
        )["chart_enabled"] is False

        long_text = "Заголовок\n" + "\n".join(f"Строка {index}: " + "x" * 90 for index in range(30))
        caption = service.build_photo_caption(long_text)

        assert service._telegram_text_units(caption) <= service.PHOTO_CAPTION_LIMIT
        assert caption.endswith("… Остальные детали — в приложении.")
        assert caption.startswith("Заголовок\n")

        emoji_caption = service.build_photo_caption("📈" * 700)
        assert service._telegram_text_units(emoji_caption) <= service.PHOTO_CAPTION_LIMIT
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
