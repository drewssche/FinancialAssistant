import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user_id
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


def test_dashboard_all_time_empty(client: TestClient):
    summary = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["income_total"] in ("0", "0.00")
    assert payload["expense_total"] in ("0", "0.00")
    assert payload["balance"] in ("0", "0.00")
    assert payload["debt_lend_outstanding"] in ("0", "0.00")
    assert payload["debt_borrow_outstanding"] in ("0", "0.00")
    assert payload["debt_net_position"] in ("0", "0.00")
    assert payload["active_debt_cards"] == 0


def test_dashboard_all_time_uses_first_operation_date(client: TestClient):
    client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "100.00",
            "operation_date": "2026-01-10",
            "note": "A",
        },
    )
    client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "250.00",
            "operation_date": "2026-03-01",
            "note": "B",
        },
    )
    summary = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["income_total"] == "250.00"
    assert payload["expense_total"] == "100.00"
    assert payload["balance"] == "150.00"


def test_dashboard_summary_includes_debt_metrics(client: TestClient):
    client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Иван",
            "direction": "lend",
            "principal": "300.00",
            "start_date": "2026-03-01",
        },
    )
    client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Анна",
            "direction": "borrow",
            "principal": "120.00",
            "start_date": "2026-03-02",
        },
    )
    summary = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["debt_lend_outstanding"] == "300.00"
    assert payload["debt_borrow_outstanding"] == "120.00"
    assert payload["debt_net_position"] == "180.00"
    assert payload["active_debt_cards"] == 2
