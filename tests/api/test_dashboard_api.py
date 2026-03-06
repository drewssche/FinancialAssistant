import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user_id
from app.core.cache import reset_cache_for_tests
from app.core.metrics import reset_metrics_for_tests
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
def reset_dashboard_metrics():
    reset_cache_for_tests()
    reset_metrics_for_tests()
    yield
    reset_cache_for_tests()
    reset_metrics_for_tests()


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


def test_dashboard_summary_metrics_track_cache_and_invalidation(client: TestClient):
    first = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert first.status_code == 200
    second = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert second.status_code == 200
    client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "42.00",
            "operation_date": "2026-03-06",
            "note": "invalidate",
        },
    )
    metrics = client.get("/api/v1/dashboard/summary/metrics")
    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["cache_miss_total"] == 1
    assert payload["cache_hit_total"] == 1
    assert payload["cache_invalidate_total"] >= 1
    assert payload["latency_total"]["samples"] >= 2
    assert isinstance(payload["endpoint_request_totals"], dict)
    assert payload["endpoint_request_totals"].get("GET /api/v1/dashboard/summary", 0) >= 2


def test_dashboard_summary_cache_is_invalidated_after_operation_update_and_delete(client: TestClient):
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "100.00",
            "operation_date": "2026-03-06",
            "note": "cache-op",
        },
    )
    assert created.status_code == 201
    operation_id = created.json()["id"]

    initial = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert initial.status_code == 200
    assert initial.json()["expense_total"] == "100.00"

    warm = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert warm.status_code == 200
    assert warm.json()["expense_total"] == "100.00"

    updated = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"amount": "250.00"},
    )
    assert updated.status_code == 200

    after_update = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert after_update.status_code == 200
    assert after_update.json()["expense_total"] == "250.00"

    deleted = client.delete(f"/api/v1/operations/{operation_id}")
    assert deleted.status_code == 204

    after_delete = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert after_delete.status_code == 200
    assert after_delete.json()["expense_total"] == "0.00"


def test_dashboard_summary_cache_is_invalidated_after_debt_mutations(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Кэш Тест",
            "direction": "lend",
            "principal": "120.00",
            "start_date": "2026-03-06",
        },
    )
    assert created.status_code == 201
    debt_id = created.json()["id"]

    initial = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert initial.status_code == 200
    assert initial.json()["debt_lend_outstanding"] == "120.00"
    assert initial.json()["active_debt_cards"] == 1

    warm = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert warm.status_code == 200
    assert warm.json()["debt_lend_outstanding"] == "120.00"

    repaid = client.post(
        f"/api/v1/debts/{debt_id}/repayments",
        json={"amount": "20.00", "repayment_date": "2026-03-06"},
    )
    assert repaid.status_code == 201

    after_repayment = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert after_repayment.status_code == 200
    assert after_repayment.json()["debt_lend_outstanding"] == "100.00"
    assert after_repayment.json()["active_debt_cards"] == 1

    deleted = client.delete(f"/api/v1/debts/{debt_id}")
    assert deleted.status_code == 204

    after_delete = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert after_delete.status_code == 200
    assert after_delete.json()["debt_lend_outstanding"] in ("0", "0.00")
    assert after_delete.json()["active_debt_cards"] == 0
