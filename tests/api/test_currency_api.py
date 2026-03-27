import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user_id
from app.core.cache import reset_cache_for_tests
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db
from app.main import app


def _override_current_user_id() -> int:
    return 1


@pytest.fixture
def client():
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
    app.dependency_overrides[get_current_user_id] = _override_current_user_id

    db = testing_session()
    db.add(User(id=1, display_name="Tester", status="active"))
    db.commit()
    db.close()

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_cache():
    reset_cache_for_tests()
    yield
    reset_cache_for_tests()


def test_currency_trade_overview_and_current_rate(client: TestClient):
    created = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "100",
            "unit_price": "3.20",
            "fee": "2.00",
            "trade_date": "2026-03-01",
            "note": "Первая покупка",
        },
    )
    assert created.status_code == 201, created.text

    rate = client.put(
        "/api/v1/currency/rates/current",
        json={
            "currency": "USD",
            "rate": "3.30",
            "rate_date": "2026-03-27",
            "source": "manual",
        },
    )
    assert rate.status_code == 200, rate.text

    overview = client.get("/api/v1/currency/overview")
    assert overview.status_code == 200, overview.text
    payload = overview.json()
    assert payload["base_currency"] == "BYN"
    assert payload["tracked_currencies"] == ["USD", "EUR"]
    assert payload["active_positions"] == 1
    assert payload["total_book_value"] == "322.00"
    assert payload["total_current_value"] == "330.00"
    assert payload["total_result_value"] == "8.00"
    assert len(payload["positions"]) == 1
    assert payload["positions"][0]["currency"] == "USD"
    assert payload["positions"][0]["average_buy_rate"] == "3.220000"
    assert payload["positions"][0]["current_rate"] == "3.300000"
    assert payload["positions"][0]["current_rate_date"] == "2026-03-27"
    assert payload["positions"][0]["result_value"] == "8.00"


def test_currency_trade_rejects_sell_above_available_balance(client: TestClient):
    response = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "sell",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "10",
            "unit_price": "3.35",
            "fee": "0",
            "trade_date": "2026-03-05",
        },
    )
    assert response.status_code == 400
    assert "Not enough currency balance to sell" in response.json()["detail"]


def test_currency_rate_history_returns_chronological_points(client: TestClient):
    client.put(
        "/api/v1/currency/rates/current",
        json={
            "currency": "USD",
            "rate": "3.21",
            "rate_date": "2026-03-20",
        },
    )
    client.put(
        "/api/v1/currency/rates/current",
        json={
            "currency": "USD",
            "rate": "3.25",
            "rate_date": "2026-03-21",
        },
    )
    client.put(
        "/api/v1/currency/rates/current",
        json={
            "currency": "USD",
            "rate": "3.24",
            "rate_date": "2026-03-22",
        },
    )

    response = client.get("/api/v1/currency/rates/history", params={"currency": "USD", "limit": 10})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert [item["rate_date"] for item in payload] == ["2026-03-20", "2026-03-21", "2026-03-22"]
    assert [item["rate"] for item in payload] == ["3.210000", "3.250000", "3.240000"]
