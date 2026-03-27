from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import User, UserPreference
from app.services.currency_rate_refresh_service import CurrencyRateRefreshService


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def test_refresh_user_tracked_rates_upserts_missing_daily_snapshots(monkeypatch):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "currency": {"tracked_currencies": ["USD", "EUR"]},
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.commit()

        class _FakeResponse:
            def __init__(self, rate: float):
                self._rate = rate

            def raise_for_status(self):
                return None

            def json(self):
                return {"Cur_OfficialRate": self._rate}

        class _FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def get(self, url: str):
                if "USD" in url:
                    return _FakeResponse(3.27)
                if "EUR" in url:
                    return _FakeResponse(3.51)
                raise AssertionError(url)

        monkeypatch.setattr("app.services.currency_rate_refresh_service.httpx.Client", _FakeClient)

        refreshed = CurrencyRateRefreshService(db).refresh_user_tracked_rates(
            user_id=1,
            prefs={"ui": {"timezone": "UTC"}},
        )

        assert len(refreshed) == 2
        overview = CurrencyRateRefreshService(db).currency_service.get_overview(user_id=1)
        rates = {item["currency"]: item for item in overview["current_rates"]}
        assert str(rates["USD"]["rate"]) == "3.270000"
        assert str(rates["EUR"]["rate"]) == "3.510000"
        assert rates["USD"]["rate_date"] == datetime.now(ZoneInfo("UTC")).date()
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_backfill_user_rate_history_saves_missing_days(monkeypatch):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "currency": {"tracked_currencies": ["USD"]},
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.commit()

        class _FakeResponse:
            def __init__(self, rate: float):
                self._rate = rate

            def raise_for_status(self):
                return None

            def json(self):
                return {"Cur_OfficialRate": self._rate}

        class _FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def get(self, url: str):
                if "ondate=2026-03-01" in url:
                    return _FakeResponse(3.21)
                if "ondate=2026-03-02" in url:
                    return _FakeResponse(3.22)
                if "ondate=2026-03-03" in url:
                    return _FakeResponse(3.23)
                raise AssertionError(url)

        monkeypatch.setattr("app.services.currency_rate_refresh_service.httpx.Client", _FakeClient)

        refreshed = CurrencyRateRefreshService(db).backfill_user_rate_history(
            user_id=1,
            currency="USD",
            date_from=date(2026, 3, 1),
            date_to=date(2026, 3, 3),
        )

        assert len(refreshed) == 3
        overview = CurrencyRateRefreshService(db).currency_service.get_rate_history(
            user_id=1,
            currency="USD",
            date_from=date(2026, 3, 1),
            date_to=date(2026, 3, 3),
        )
        assert [item["rate_date"] for item in overview] == [date(2026, 3, 1), date(2026, 3, 2), date(2026, 3, 3)]
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_refresh_user_tracked_rates_keeps_last_available_snapshot_until_new_official_date(monkeypatch):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "currency": {"tracked_currencies": ["USD"]},
                    "ui": {"timezone": "UTC", "currency": "BYN"},
                },
            )
        )
        db.commit()

        service = CurrencyRateRefreshService(db)
        yesterday = date.today() - timedelta(days=1)
        service.currency_service.upsert_rate(
            user_id=1,
            currency="USD",
            rate=3.27,
            rate_date=yesterday,
            source="nbrb_auto",
        )

        class _FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "Cur_OfficialRate": 3.27,
                }

        class _FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def get(self, url: str):
                if "USD" in url:
                    return _FakeResponse()
                raise AssertionError(url)

        monkeypatch.setattr("app.services.currency_rate_refresh_service.httpx.Client", _FakeClient)

        refreshed = service.refresh_user_tracked_rates(
            user_id=1,
            prefs={"ui": {"timezone": "UTC"}},
        )

        assert refreshed == []
        history = service.currency_service.get_rate_history(user_id=1, currency="USD", limit=10)
        assert len(history) == 1
        assert history[0]["rate_date"] == yesterday
        overview = service.currency_service.get_overview(user_id=1)
        rates = {item["currency"]: item for item in overview["current_rates"]}
        assert rates["USD"]["rate_date"] == yesterday
        assert rates["USD"]["change_value"] is None
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
