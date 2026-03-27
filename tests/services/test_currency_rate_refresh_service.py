from datetime import date

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
        assert rates["USD"]["rate_date"] == date.today()
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
