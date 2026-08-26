import base64
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json

from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import FxBankRateSnapshot, User, UserPreference
from app.repositories.currency_repo import CurrencyRepository
from app.services.bank_currency_rate_refresh_service import (
    BankCurrencyQuote,
    BankCurrencyRateRefreshService,
)


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def test_parse_priorbank_online_rates():
    payload = {
        "resultEBank": json.dumps(
            {
                "simpleCurrencyList": [
                    {
                        "baseCurrency": 840,
                        "baseCurrencyNominal": 1,
                        "ratedCurrency": 933,
                        "buyRate": "3.0100",
                        "sellRate": "3.0700",
                        "validFromDate": "18.08.2026",
                        "validFromTime": "10:30",
                    },
                    {
                        "baseCurrency": 643,
                        "baseCurrencyNominal": 100,
                        "ratedCurrency": 933,
                        "buyRate": "3.5000",
                        "sellRate": "3.6500",
                    },
                ]
            }
        )
    }

    quotes = BankCurrencyRateRefreshService._parse_priorbank(payload)

    assert [(item.currency, item.scale) for item in quotes] == [("USD", 1), ("RUB", 100)]
    assert quotes[0].buy_rate == Decimal("3.010000")
    assert quotes[0].sell_rate == Decimal("3.070000")
    assert quotes[0].channel == "online"


def test_parse_technobank_cash_rates():
    raw = {
        "items": [
            {
                "cityId": 37,
                "title": "ЦБУ",
                "address": "Минск",
                "exchangeRates": [
                    {
                        "currency": "EUR",
                        "quantity": 1,
                        "buying": {"value": "3.4200"},
                        "sale": {"value": "3.5100"},
                    },
                    {
                        "currency": "CNY",
                        "quantity": 10,
                        "buying": {"value": "4.4500"},
                        "sale": {"value": "4.6500"},
                    },
                ],
            }
        ]
    }
    payload = {"encoded": base64.b64encode(json.dumps(raw).encode()).decode()}

    quotes = BankCurrencyRateRefreshService._parse_technobank(payload)

    assert len(quotes) == 2
    assert quotes[0].currency == "EUR"
    assert quotes[0].location_name == "ЦБУ · Минск"
    assert quotes[0].buy_rate == Decimal("3.420000")
    assert quotes[1].currency == "CNY"
    assert quotes[1].scale == 1
    assert quotes[1].buy_rate == Decimal("0.445000")


def test_parse_bsb_cash_rates():
    payload = {
        "fromTime": 1787047200000,
        "rates": [
            {
                "buyCurrencyName": "RUB",
                "sellCurrencyName": "BYN",
                "buyCurrencyScale": 100,
                "scaledBuyAmount": "3.4800",
                "scaledSellAmount": "3.6200",
            }
        ],
    }

    quotes = BankCurrencyRateRefreshService._parse_bsb(payload)

    assert len(quotes) == 1
    assert quotes[0].currency == "RUB"
    assert quotes[0].scale == 100
    assert quotes[0].quoted_at == datetime.fromtimestamp(1787047200, tz=timezone.utc)


def test_parse_sber_selects_best_cash_buy_and_sell():
    payload = {
        "rates": [
            {
                "sourceCurrency": "USD",
                "targetCurrency": "BYN",
                "direction": "buy",
                "exchangeRate": "3.0100",
                "scaleCurrency": 1,
                "branchName": "Офис 1",
            },
            {
                "sourceCurrency": "USD",
                "targetCurrency": "BYN",
                "direction": "buy",
                "exchangeRate": "3.0200",
                "scaleCurrency": 1,
                "branchName": "Офис 2",
            },
            {
                "sourceCurrency": "USD",
                "targetCurrency": "BYN",
                "direction": "sell",
                "exchangeRate": "3.0900",
                "scaleCurrency": 1,
            },
            {
                "sourceCurrency": "USD",
                "targetCurrency": "BYN",
                "direction": "sell",
                "exchangeRate": "3.0800",
                "scaleCurrency": 1,
            },
        ]
    }

    quotes = BankCurrencyRateRefreshService._parse_sber(payload)

    assert len(quotes) == 1
    assert quotes[0].buy_rate == Decimal("3.020000")
    assert quotes[0].sell_rate == Decimal("3.080000")
    assert quotes[0].location_name == "Офис 2"


def test_quote_date_uses_minsk_boundary_and_prefers_provider_timestamp():
    quote = BankCurrencyQuote(
        bank_code="technobank",
        bank_name="Технобанк",
        currency="EUR",
        scale=1,
        buy_rate=Decimal("3.49"),
        sell_rate=Decimal("3.53"),
        channel="cash",
        location_name=None,
        source_url="https://example.test/rates",
        quoted_at=datetime(2026, 8, 25, 21, 30, tzinfo=timezone.utc),
    )

    assert BankCurrencyRateRefreshService._quote_date(
        quote=quote,
        fetched_at=datetime(2026, 8, 25, 20, 0, tzinfo=timezone.utc),
    ) == date(2026, 8, 26)

    quote_without_timestamp = BankCurrencyQuote(
        **{**quote.__dict__, "quoted_at": None},
    )
    assert BankCurrencyRateRefreshService._quote_date(
        quote=quote_without_timestamp,
        fetched_at=datetime(2026, 8, 26, 20, 59, tzinfo=timezone.utc),
    ) == date(2026, 8, 26)
    assert BankCurrencyRateRefreshService._quote_date(
        quote=quote_without_timestamp,
        fetched_at=datetime(2026, 8, 26, 21, 0, tzinfo=timezone.utc),
    ) == date(2026, 8, 27)


def test_daily_history_upsert_keeps_one_latest_point_per_day_and_next_day_separate():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        repo = CurrencyRepository(db)
        common = {
            "bank_code": "technobank",
            "bank_name": "Технобанк",
            "currency": "EUR",
            "base_currency": "BYN",
            "scale": 1,
            "channel": "cash",
            "location_name": "Минск",
            "source_url": "https://example.test/rates",
            "quoted_at": None,
        }
        repo.upsert_bank_rate_snapshot(
            **common,
            rate_date=date(2026, 8, 26),
            buy_rate=Decimal("3.490000"),
            sell_rate=Decimal("3.530000"),
            fetched_at=datetime(2026, 8, 26, 8, 0, tzinfo=timezone.utc),
        )
        repo.upsert_bank_rate_snapshot(
            **common,
            rate_date=date(2026, 8, 26),
            buy_rate=Decimal("3.500000"),
            sell_rate=Decimal("3.540000"),
            fetched_at=datetime(2026, 8, 26, 9, 0, tzinfo=timezone.utc),
        )
        # A delayed concurrent refresh must not replace the newer observation.
        repo.upsert_bank_rate_snapshot(
            **common,
            rate_date=date(2026, 8, 26),
            buy_rate=Decimal("3.480000"),
            sell_rate=Decimal("3.520000"),
            fetched_at=datetime(2026, 8, 26, 8, 30, tzinfo=timezone.utc),
        )
        repo.upsert_bank_rate_snapshot(
            **common,
            rate_date=date(2026, 8, 27),
            buy_rate=Decimal("3.510000"),
            sell_rate=Decimal("3.550000"),
            fetched_at=datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc),
        )
        db.commit()

        rows = list(db.scalars(select(FxBankRateSnapshot).order_by(FxBankRateSnapshot.rate_date)))
        assert [(row.rate_date, row.buy_rate, row.sell_rate) for row in rows] == [
            (date(2026, 8, 26), Decimal("3.500000"), Decimal("3.540000")),
            (date(2026, 8, 27), Decimal("3.510000"), Decimal("3.550000")),
        ]
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_history_respects_user_bank_preferences_and_limits_by_calendar_days():
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
                        "bank_rate_banks": ["technobank"],
                    },
                    "ui": {"currency": "BYN"},
                },
            )
        )
        repo = CurrencyRepository(db)
        for bank_code, bank_name in (("technobank", "Технобанк"), ("priorbank", "Приорбанк")):
            for offset in range(3):
                repo.upsert_bank_rate_snapshot(
                    bank_code=bank_code,
                    bank_name=bank_name,
                    currency="EUR",
                    base_currency="BYN",
                    rate_date=date(2026, 8, 24) + timedelta(days=offset),
                    scale=1,
                    buy_rate=Decimal("3.490000") + Decimal(offset) / 100,
                    sell_rate=Decimal("3.530000") + Decimal(offset) / 100,
                    channel="cash",
                    location_name=None,
                    source_url=None,
                    quoted_at=None,
                    fetched_at=datetime(2026, 8, 24 + offset, 8, tzinfo=timezone.utc),
                )
        db.commit()

        points = BankCurrencyRateRefreshService(db).get_user_rate_history(
            user_id=1,
            currency="EUR",
            bank_codes=["priorbank", "technobank"],
            limit=2,
        )

        assert {point["bank_code"] for point in points} == {"technobank"}
        assert [point["rate_date"] for point in points] == [date(2026, 8, 25), date(2026, 8, 26)]
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
