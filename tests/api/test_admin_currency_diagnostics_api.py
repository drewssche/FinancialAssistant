from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_admin_user
from app.db.base import Base
from app.db.models import FxRateSnapshot, User, UserPreference
from app.db.session import get_db
from app.main import app


def _override_admin_user() -> User:
    return User(id=999, display_name="Admin", status="active")


@pytest.fixture
def client_and_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_admin_user] = _override_admin_user

    test_client = TestClient(app)
    yield test_client, testing_session

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_admin_currency_diagnostics_aggregates_runtime_state(client_and_sessionmaker):
    client, SessionLocal = client_and_sessionmaker
    app.dependency_overrides[get_current_admin_user] = _override_admin_user
    try:
        with SessionLocal() as db:
            db.add(User(id=1, display_name="One", status="active"))
            db.add(User(id=2, display_name="Two", status="active"))
            db.add(
                UserPreference(
                    user_id=1,
                    preferences_version=1,
                    data={
                        "currency": {
                            "tracked_currencies": ["USD", "EUR"],
                            "telegram_digest_enabled": True,
                            "currency_alerts": {"USD": {"above_rate": "3.3000"}},
                        },
                        "ui": {"currency": "BYN"},
                    },
                )
            )
            db.add(
                UserPreference(
                    user_id=2,
                    preferences_version=1,
                    data={
                        "currency": {
                            "tracked_currencies": ["USD"],
                            "telegram_digest_enabled": False,
                        },
                        "ui": {"currency": "BYN"},
                    },
                )
            )
            db.add(
                FxRateSnapshot(
                    user_id=1,
                    currency="USD",
                    rate=Decimal("3.4200"),
                    rate_date=date.today(),
                    source="manual",
                )
            )
            db.add(
                FxRateSnapshot(
                    user_id=1,
                    currency="EUR",
                    rate=Decimal("3.5000"),
                    rate_date=date.today(),
                    source="manual",
                )
            )
            db.add(
                FxRateSnapshot(
                    user_id=2,
                    currency="USD",
                    rate=Decimal("3.4100"),
                    rate_date=date.today() - timedelta(days=1),
                    source="manual",
                )
            )
            db.commit()

        response = client.get("/api/v1/admin/currency-diagnostics")
        assert response.status_code == 200
        payload = response.json()
        assert payload["tracked_users"] == 2
        assert payload["tracked_currency_slots"] == 3
        assert payload["digest_enabled_users"] == 1
        assert payload["alert_rules_count"] == 1
        usd = next(item for item in payload["items"] if item["currency"] == "USD")
        eur = next(item for item in payload["items"] if item["currency"] == "EUR")
        assert usd["tracked_users"] == 2
        assert usd["digest_users"] == 1
        assert usd["alert_rules"] == 1
        assert usd["stale_users"] == 1
        assert eur["missing_users"] == 0
    finally:
        app.dependency_overrides.pop(get_current_admin_user, None)
