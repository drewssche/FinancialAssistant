from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import ActivityEvent, AuthIdentity, FxRateSnapshot, FxTrade, User, UserPreference
from app.services.telegram_currency_digest_bot_service import (
    TelegramCurrencyDigestBotService,
    TelegramCurrencyDigestDelivery,
    TelegramCurrencyDigestIdentityMissingError,
    TelegramCurrencyDigestTrackedCurrenciesMissingError,
    currency_digest_delivery_lock_name,
)


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


def test_manual_delivery_uses_cached_rates_even_when_schedule_is_disabled(monkeypatch):
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
                        "telegram_digest_enabled": False,
                        "telegram_digest_chart_enabled": False,
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.add(
            FxRateSnapshot(
                user_id=1,
                currency="USD",
                rate=Decimal("3.25"),
                rate_date=date(2026, 8, 26),
                source="nbrb_auto_unit",
            )
        )
        db.commit()

        service = TelegramCurrencyDigestBotService(db)
        monkeypatch.setattr(
            service.refresh_service,
            "refresh_user_tracked_rates",
            lambda **kwargs: pytest.fail("manual digest must not refresh NBRB rates"),
        )
        monkeypatch.setattr(
            service.bank_refresh_service,
            "refresh_user_selected_rates",
            lambda **kwargs: pytest.fail("manual digest must not refresh bank rates"),
        )

        delivery = service.build_manual_delivery(user_id=1)

        assert delivery.chat_id == "100500"
        assert delivery.tracked_currencies == ["USD"]
        assert "USD: курс НБРБ 3.2500" in delivery.text
        assert delivery.photo_png is None
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_manual_delivery_requires_users_own_telegram_identity_and_tracked_currency():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add_all(
            [
                User(id=1, display_name="Without Telegram", status="active"),
                User(id=2, display_name="Other", status="active"),
                AuthIdentity(user_id=2, provider="telegram", provider_user_id="222"),
                UserPreference(
                    user_id=1,
                    preferences_version=1,
                    data={"currency": {"tracked_currencies": ["USD"]}},
                ),
            ]
        )
        db.commit()
        service = TelegramCurrencyDigestBotService(db)

        with pytest.raises(TelegramCurrencyDigestIdentityMissingError):
            service.build_manual_delivery(user_id=1)

        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="111"))
        preference = db.get(UserPreference, 1)
        preference.data = {"currency": {"tracked_currencies": []}}
        db.commit()

        with pytest.raises(TelegramCurrencyDigestTrackedCurrenciesMissingError):
            service.build_manual_delivery(user_id=1)
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_manual_delivery_before_schedule_does_not_consume_slot_and_is_audited(monkeypatch):
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
                        "telegram_digest_enabled": True,
                        "telegram_digest_time": "14:00",
                        "telegram_digest_chart_enabled": False,
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.commit()

        class _FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):  # noqa: ANN001
                return cls(2026, 8, 26, 12, 0, tzinfo=tz)

        monkeypatch.setattr(
            "app.services.telegram_currency_digest_bot_service.datetime",
            _FrozenDateTime,
        )
        service = TelegramCurrencyDigestBotService(db)
        delivery = service.build_manual_delivery(user_id=1)

        receipt = service.mark_manual_delivery_sent(delivery, delivery_format="text")

        assert receipt.scheduled_slot_consumed is False
        preference = db.get(UserPreference, 1)
        assert "last_digest_sent_on" not in preference.data["currency"]
        activity = db.query(ActivityEvent).one()
        assert activity.actor_user_id == 1
        assert activity.source == "web"
        assert activity.metadata_json["delivery_trigger"] == "manual"
        assert activity.metadata_json["scheduled_slot_consumed"] is False
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_manual_delivery_after_schedule_consumes_unsent_slot(monkeypatch):
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
                        "telegram_digest_enabled": True,
                        "telegram_digest_time": "10:00",
                        "telegram_digest_chart_enabled": False,
                        "digest_delivery_claimed_on": "2026-08-26",
                    },
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.commit()

        class _FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):  # noqa: ANN001
                return cls(2026, 8, 26, 12, 0, tzinfo=tz)

        monkeypatch.setattr(
            "app.services.telegram_currency_digest_bot_service.datetime",
            _FrozenDateTime,
        )
        service = TelegramCurrencyDigestBotService(db)
        delivery = TelegramCurrencyDigestDelivery(
            chat_id="100500",
            text="Digest",
            user_id=1,
            tracked_currencies=["USD"],
        )

        receipt = service.mark_manual_delivery_sent(delivery, delivery_format="photo")

        assert receipt.scheduled_slot_consumed is True
        preference = db.get(UserPreference, 1)
        assert preference.data["currency"]["last_digest_sent_on"] == "2026-08-26"
        assert "digest_delivery_claimed_on" not in preference.data["currency"]
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_currency_digest_delivery_lock_is_scoped_per_user():
    assert currency_digest_delivery_lock_name(7) == "telegram_currency_digest_delivery:7"
    assert currency_digest_delivery_lock_name(7) != currency_digest_delivery_lock_name(8)


def test_scheduler_claim_rechecks_manual_marker_from_another_session(monkeypatch):
    engine, SessionLocal = _make_session()
    scheduler_db = SessionLocal()
    manual_db = SessionLocal()
    try:
        scheduler_db.add(User(id=1, display_name="Tester", status="active"))
        scheduler_db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500"))
        scheduler_db.add(
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
        scheduler_db.commit()

        class _FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):  # noqa: ANN001
                return cls(2026, 8, 26, 12, 0, tzinfo=tz)

        monkeypatch.setattr(
            "app.services.telegram_currency_digest_bot_service.datetime",
            _FrozenDateTime,
        )
        service = TelegramCurrencyDigestBotService(scheduler_db)
        monkeypatch.setattr(service.refresh_service, "refresh_user_tracked_rates", lambda **kwargs: [])
        candidate = service.list_due_deliveries()[0]

        preference = manual_db.get(UserPreference, 1)
        latest = dict(preference.data)
        currency = dict(latest["currency"])
        currency["last_digest_sent_on"] = "2026-08-26"
        latest["currency"] = currency
        preference.data = latest
        manual_db.commit()

        assert service.claim_delivery(candidate) is False
        scheduler_db.expire_all()
        assert "digest_delivery_claimed_on" not in scheduler_db.get(UserPreference, 1).data["currency"]
    finally:
        manual_db.close()
        scheduler_db.close()
        Base.metadata.drop_all(bind=engine)


def test_manual_confirmation_merges_marker_into_concurrently_updated_preferences(monkeypatch):
    engine, SessionLocal = _make_session()
    delivery_db = SessionLocal()
    settings_db = SessionLocal()
    verification_db = SessionLocal()
    try:
        delivery_db.add(User(id=1, display_name="Tester", status="active"))
        delivery_db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500"))
        delivery_db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "dashboard": {"period": "day"},
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
        delivery_db.commit()

        class _FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):  # noqa: ANN001
                return cls(2026, 8, 26, 12, 0, tzinfo=tz)

        monkeypatch.setattr(
            "app.services.telegram_currency_digest_bot_service.datetime",
            _FrozenDateTime,
        )
        service = TelegramCurrencyDigestBotService(delivery_db)
        delivery = service.build_manual_delivery(user_id=1)

        preference = settings_db.get(UserPreference, 1)
        updated = dict(preference.data)
        updated["dashboard"] = {"period": "year"}
        updated_currency = dict(updated["currency"])
        updated_currency["tracked_currencies"] = ["EUR"]
        updated_currency["custom_browser_setting"] = "preserve-me"
        updated["currency"] = updated_currency
        preference.data = updated
        preference.preferences_version = 2
        settings_db.commit()

        receipt = service.mark_manual_delivery_sent(delivery, delivery_format="text")

        assert receipt.scheduled_slot_consumed is True
        verification_db.expire_all()
        persisted = verification_db.get(UserPreference, 1)
        assert persisted.preferences_version == 2
        assert persisted.data["dashboard"] == {"period": "year"}
        assert persisted.data["currency"]["tracked_currencies"] == ["EUR"]
        assert persisted.data["currency"]["custom_browser_setting"] == "preserve-me"
        assert persisted.data["currency"]["last_digest_sent_on"] == "2026-08-26"
    finally:
        verification_db.close()
        settings_db.close()
        delivery_db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.mark.parametrize(
    ("enabled", "last_sent", "expected_marker"),
    [
        (True, "2026-08-26", "2026-08-26"),
        (False, "", None),
    ],
)
def test_manual_confirmation_does_not_consume_closed_or_disabled_schedule(
    monkeypatch,
    enabled,
    last_sent,
    expected_marker,
):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        currency = {
            "tracked_currencies": ["USD"],
            "telegram_digest_enabled": enabled,
            "telegram_digest_time": "00:00",
        }
        if last_sent:
            currency["last_digest_sent_on"] = last_sent
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(UserPreference(
            user_id=1,
            preferences_version=1,
            data={"currency": currency, "ui": {"timezone": "UTC"}},
        ))
        db.commit()

        class _FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):  # noqa: ANN001
                return cls(2026, 8, 26, 12, 0, tzinfo=tz)

        monkeypatch.setattr(
            "app.services.telegram_currency_digest_bot_service.datetime",
            _FrozenDateTime,
        )
        delivery = TelegramCurrencyDigestDelivery(
            chat_id="100500",
            text="Digest",
            user_id=1,
            tracked_currencies=["USD"],
        )

        receipt = TelegramCurrencyDigestBotService(db).mark_manual_delivery_sent(
            delivery,
            delivery_format="text",
        )

        assert receipt.scheduled_slot_consumed is False
        persisted_marker = db.get(UserPreference, 1).data["currency"].get("last_digest_sent_on")
        assert persisted_marker == expected_marker
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.mark.parametrize(
    ("schedule_time", "expected_consumed"),
    [("14:00", False), ("10:00", True)],
)
def test_ambiguous_manual_timeout_only_consumes_due_schedule(
    monkeypatch,
    schedule_time,
    expected_consumed,
):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(UserPreference(
            user_id=1,
            preferences_version=1,
            data={
                "currency": {
                    "tracked_currencies": ["USD"],
                    "telegram_digest_enabled": True,
                    "telegram_digest_time": schedule_time,
                },
                "ui": {"timezone": "UTC"},
            },
        ))
        db.commit()

        class _FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):  # noqa: ANN001
                return cls(2026, 8, 26, 12, 0, tzinfo=tz)

        monkeypatch.setattr(
            "app.services.telegram_currency_digest_bot_service.datetime",
            _FrozenDateTime,
        )
        delivery = TelegramCurrencyDigestDelivery(
            chat_id="100500",
            text="Digest",
            user_id=1,
            tracked_currencies=["USD"],
        )

        consumed = TelegramCurrencyDigestBotService(db).mark_manual_delivery_unconfirmed(delivery)

        assert consumed is expected_consumed
        preference = db.get(UserPreference, 1)
        marker = preference.data["currency"].get("last_digest_sent_on")
        assert marker == ("2026-08-26" if expected_consumed else None)
        assert db.query(ActivityEvent).count() == 0
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
