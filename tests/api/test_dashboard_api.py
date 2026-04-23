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
    assert "date_from" in payload
    assert "date_to" in payload
    assert payload["income_total"] in ("0", "0.00")
    assert payload["expense_total"] in ("0", "0.00")
    assert payload["balance"] in ("0", "0.00")
    assert payload["debt_lend_outstanding"] in ("0", "0.00")
    assert payload["debt_borrow_outstanding"] in ("0", "0.00")
    assert payload["debt_net_position"] in ("0", "0.00")
    assert payload["active_debt_cards"] == 0


def test_dashboard_summary_survives_inconsistent_fx_history(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    def raise_broken_history(self, *, user_id: int):
        raise ValueError("Broken FX history for USD: sell exceeds available quantity")

    monkeypatch.setattr(
        "app.services.dashboard_service.CurrencyService.compute_positions",
        raise_broken_history,
    )

    summary = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["currency_current_value"] in ("0", "0.00")
    assert payload["currency_total_result_value"] in ("0", "0.00")
    assert payload["tracked_currency_positions"] == []


def test_dashboard_summary_survives_unexpected_currency_error(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    def raise_unexpected_currency_error(self, *, user_id: int):
        raise RuntimeError("currency backend is temporarily unavailable")

    monkeypatch.setattr(
        "app.services.dashboard_service.CurrencyService.compute_positions",
        raise_unexpected_currency_error,
    )

    summary = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["currency_current_value"] in ("0", "0.00")
    assert payload["currency_total_result_value"] in ("0", "0.00")
    assert payload["tracked_currency_positions"] == []


def test_dashboard_summary_survives_debt_summary_error(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    def raise_debt_error(self, *, user_id: int):
        raise RuntimeError("debt backend is temporarily unavailable")

    monkeypatch.setattr(
        "app.services.dashboard_service.DebtService.summary_active_totals_current_base",
        raise_debt_error,
    )

    summary = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})

    assert summary.status_code == 200
    payload = summary.json()
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
    assert payload["date_from"] == "2026-01-10"
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


def test_dashboard_summary_uses_current_base_equivalent_for_foreign_currency_debt(client: TestClient):
    rate = client.put(
        "/api/v1/currency/rates/current",
        json={
            "currency": "USD",
            "rate": "3.50",
            "rate_date": "2026-03-28",
            "source": "manual",
        },
    )
    assert rate.status_code == 200

    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Игорь",
            "direction": "lend",
            "principal": "100.00",
            "currency": "USD",
            "start_date": "2026-03-07",
        },
    )
    assert created.status_code == 201

    response = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["debt_lend_outstanding"] == "350.00"
    assert payload["debt_borrow_outstanding"] in ("0", "0.00")
    assert payload["debt_net_position"] == "350.00"


def test_dashboard_summary_excludes_forgiven_debt_from_active_totals(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Михаил",
            "direction": "lend",
            "principal": "180.00",
            "start_date": "2026-03-05",
        },
    )
    assert created.status_code == 201

    forgiven = client.post(
        f"/api/v1/debts/{created.json()['id']}/forgivenesses",
        json={"amount": "180.00", "forgiven_date": "2026-03-21"},
    )
    assert forgiven.status_code == 201

    response = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["debt_lend_outstanding"] in ("0", "0.00")
    assert payload["active_debt_cards"] == 0


def test_dashboard_summary_includes_currency_metrics(client: TestClient):
    rate_response = client.put(
        "/api/v1/currency/rates/current",
        json={
            "currency": "USD",
            "rate": "3.40",
            "rate_date": "2026-03-27",
        },
    )
    assert rate_response.status_code == 200
    trade_response = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "50",
            "unit_price": "3.10",
            "fee": "0",
            "trade_date": "2026-03-01",
            "note": "USD buy",
        },
    )
    assert trade_response.status_code == 201

    summary = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["currency_book_value"] == "155.00"
    assert payload["currency_current_value"] == "170.00"
    assert payload["currency_result_value"] == "15.00"
    assert payload["balance_with_currency_result"] == "15.00"
    assert payload["currency_buy_trades_count"] == 1


def test_dashboard_summary_does_not_double_count_currency_current_value_in_combined_balance(client: TestClient):
    trade_response = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "50",
            "unit_price": "3.10",
            "fee": "0",
            "trade_date": "2026-03-01",
            "note": "USD buy",
        },
    )
    assert trade_response.status_code == 201
    rate_response = client.put(
        "/api/v1/currency/rates/current",
        json={
            "currency": "USD",
            "rate": "3.10",
            "rate_date": "2026-03-27",
        },
    )
    assert rate_response.status_code == 200

    summary = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["balance"] in ("0", "0.00")
    assert payload["currency_book_value"] == "155.00"
    assert payload["currency_current_value"] == "155.00"
    assert payload["currency_result_value"] in ("0", "0.00")
    assert payload["balance_with_currency_result"] in ("0", "0.00")
    assert payload["currency_sell_trades_count"] == 0
    assert payload["currency_buy_volume_base"] == "155.00"
    assert payload["currency_sell_volume_base"] == "0.00"
    assert payload["currency_buy_average_rate"] == "3.100000"
    assert payload["currency_sell_average_rate"] == "0.000000"
    assert payload["active_currency_positions"] == 1
    assert len(payload["tracked_currency_positions"]) == 1
    assert payload["tracked_currency_positions"][0]["currency"] == "USD"
    assert payload["tracked_currency_positions"][0]["current_rate"] == "3.100000"


def test_dashboard_debt_preview_returns_compact_active_cards(client: TestClient):
    client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Иван",
            "direction": "lend",
            "principal": "300.00",
            "start_date": "2026-03-01",
            "due_date": "2026-03-15",
        },
    )
    client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Иван",
            "direction": "lend",
            "principal": "50.00",
            "start_date": "2026-03-02",
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

    response = client.get("/api/v1/dashboard/debts/preview", params={"limit": 6})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2

    anna = payload[0]
    ivan = payload[1]

    assert anna["counterparty"] == "Анна"
    assert anna["status"] == "active"
    assert anna["outstanding_total"] == "120.00"
    assert anna["debts"][0]["direction"] == "borrow"
    assert "repayments" not in anna["debts"][0]
    assert "issuances" not in anna["debts"][0]

    assert ivan["counterparty"] == "Иван"
    assert ivan["principal_total"] == "350.00"
    assert ivan["principal_lend_total"] == "350.00"
    assert ivan["principal_borrow_total"] == "0.00"
    assert ivan["outstanding_total"] == "350.00"
    assert len(ivan["debts"]) == 1
    assert ivan["debts"][0]["principal"] == "350.00"


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


def test_dashboard_summary_checks_redis_runtime_advisory(client: TestClient, monkeypatch):
    advisory_checks: list[bool] = []
    monkeypatch.setattr(
        "app.services.dashboard_service.RedisRuntimeAdvisoryService.maybe_send_advisory",
        lambda self: advisory_checks.append(True) or False,
    )

    response = client.get("/api/v1/dashboard/summary", params={"period": "all_time"})

    assert response.status_code == 200
    assert advisory_checks == [True]


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


def test_dashboard_analytics_calendar_returns_week_rows_and_day_cells(client: TestClient):
    client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "300.00",
            "operation_date": "2026-03-02",
            "note": "salary",
        },
    )
    client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "120.00",
            "operation_date": "2026-03-03",
            "note": "food",
        },
    )
    client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "80.00",
            "operation_date": "2026-03-03",
            "note": "taxi",
        },
    )

    response = client.get("/api/v1/dashboard/analytics/calendar", params={"month": "2026-03"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["month"] == "2026-03"
    assert payload["income_total"] == "300.00"
    assert payload["expense_total"] == "200.00"
    assert payload["operations_count"] == 3
    assert len(payload["weeks"]) >= 4
    assert all(len(week["days"]) == 7 for week in payload["weeks"])
    assert any(day["date"] == "2026-03-03" and day["operations_count"] == 2 for week in payload["weeks"] for day in week["days"])


def test_dashboard_analytics_calendar_exposes_debt_and_fx_cashflow_overlay(client: TestClient):
    debt = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Иван",
            "direction": "lend",
            "principal": "50.00",
            "currency": "BYN",
            "start_date": "2026-03-03",
            "note": "дал в долг",
        },
    )
    assert debt.status_code == 201
    debt_id = debt.json()["id"]

    repaid = client.post(
        f"/api/v1/debts/{debt_id}/repayments",
        json={"amount": "20.00", "repayment_date": "2026-03-04"},
    )
    assert repaid.status_code == 201

    forgiven = client.post(
        f"/api/v1/debts/{debt_id}/forgivenesses",
        json={"amount": "10.00", "forgiven_date": "2026-03-05"},
    )
    assert forgiven.status_code == 201

    trade = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "10",
            "unit_price": "3.00",
            "fee": "1.00",
            "trade_date": "2026-03-04",
            "note": "купил валюту",
        },
    )
    assert trade.status_code == 201

    response = client.get("/api/v1/dashboard/analytics/calendar", params={"month": "2026-03"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["debt_cashflow_total"] == "-30.00"
    assert payload["debt_events_count"] == 2
    assert payload["fx_cashflow_total"] == "-31.00"
    assert payload["fx_events_count"] == 1
    assert payload["cashflow_total"] == "-61.00"
    assert payload["cashflow_events_count"] == 3

    day_03 = next(day for week in payload["weeks"] for day in week["days"] if day["date"] == "2026-03-03")
    day_04 = next(day for week in payload["weeks"] for day in week["days"] if day["date"] == "2026-03-04")
    day_05 = next(day for week in payload["weeks"] for day in week["days"] if day["date"] == "2026-03-05")

    assert day_03["debt_cashflow_total"] == "-50.00"
    assert day_03["debt_events_count"] == 1
    assert day_03["cashflow_total"] == "-50.00"
    assert day_04["debt_cashflow_total"] == "20.00"
    assert day_04["fx_cashflow_total"] == "-31.00"
    assert day_04["cashflow_total"] == "-11.00"
    assert day_05["debt_cashflow_total"] in ("0", "0.00")
    assert day_05["debt_events_count"] == 0
    assert day_05["cashflow_total"] in ("0", "0.00")


def test_dashboard_analytics_calendar_includes_debt_and_fx_cashflow(client: TestClient):
    debt_created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Alex",
            "direction": "lend",
            "principal": "150.00",
            "currency": "BYN",
            "start_date": "2026-03-04",
            "note": "loan-out",
        },
    )
    assert debt_created.status_code == 201
    debt_id = debt_created.json()["id"]

    repaid = client.post(
        f"/api/v1/debts/{debt_id}/repayments",
        json={
            "amount": "40.00",
            "repayment_date": "2026-03-06",
            "note": "partial-return",
        },
    )
    assert repaid.status_code == 201

    fx_trade = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "10",
            "unit_price": "3.00",
            "fee": "1.00",
            "trade_date": "2026-03-05",
            "note": "usd-buy",
        },
    )
    assert fx_trade.status_code == 201

    response = client.get("/api/v1/dashboard/analytics/calendar", params={"month": "2026-03"})
    assert response.status_code == 200
    payload = response.json()

    assert payload["debt_cashflow_total"] == "-110.00"
    assert payload["fx_cashflow_total"] == "-31.00"
    assert payload["cashflow_total"] == "-141.00"
    assert payload["cashflow_events_count"] == 3

    day_loan = next(day for week in payload["weeks"] for day in week["days"] if day["date"] == "2026-03-04")
    assert day_loan["debt_cashflow_total"] == "-150.00"
    assert day_loan["debt_events_count"] == 1
    assert day_loan["cashflow_total"] == "-150.00"

    day_fx = next(day for week in payload["weeks"] for day in week["days"] if day["date"] == "2026-03-05")
    assert day_fx["fx_cashflow_total"] == "-31.00"
    assert day_fx["fx_events_count"] == 1
    assert day_fx["cashflow_total"] == "-31.00"

    day_repaid = next(day for week in payload["weeks"] for day in week["days"] if day["date"] == "2026-03-06")
    assert day_repaid["debt_cashflow_total"] == "40.00"
    assert day_repaid["debt_events_count"] == 1
    assert day_repaid["cashflow_total"] == "40.00"


def test_dashboard_analytics_calendar_cache_is_invalidated_after_operation_mutation(client: TestClient):
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "50.00",
            "operation_date": "2026-03-03",
            "note": "calendar-cache-op",
        },
    )
    assert created.status_code == 201
    operation_id = created.json()["id"]

    initial = client.get("/api/v1/dashboard/analytics/calendar", params={"month": "2026-03"})
    assert initial.status_code == 200
    assert initial.json()["expense_total"] == "50.00"

    warm = client.get("/api/v1/dashboard/analytics/calendar", params={"month": "2026-03"})
    assert warm.status_code == 200
    assert warm.json()["expense_total"] == "50.00"

    updated = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"amount": "140.00"},
    )
    assert updated.status_code == 200

    after_update = client.get("/api/v1/dashboard/analytics/calendar", params={"month": "2026-03"})
    assert after_update.status_code == 200
    assert after_update.json()["expense_total"] == "140.00"


def test_dashboard_analytics_trend_returns_points_and_deltas(client: TestClient):
    client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "100.00",
            "operation_date": "2026-03-01",
            "note": "A",
        },
    )
    client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "30.00",
            "operation_date": "2026-03-02",
            "note": "B",
        },
    )
    client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "70.00",
            "operation_date": "2026-03-03",
            "note": "C",
        },
    )

    response = client.get(
        "/api/v1/dashboard/analytics/trend",
        params={
            "period": "custom",
            "date_from": "2026-03-01",
            "date_to": "2026-03-03",
            "granularity": "day",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["date_from"] == "2026-03-01"
    assert payload["date_to"] == "2026-03-03"
    assert payload["income_total"] == "170.00"
    assert payload["expense_total"] == "30.00"
    assert payload["balance"] == "140.00"
    assert payload["cashflow_total"] == "140.00"
    assert payload["operations_count"] == 3
    assert len(payload["points"]) == 3
    assert payload["points"][0]["bucket_start"] == "2026-03-01"


def test_dashboard_analytics_trend_uses_unified_cashflow(client: TestClient):
    assert client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "300.00",
            "operation_date": "2026-03-01",
            "note": "salary",
        },
    ).status_code == 201
    assert client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "120.00",
            "operation_date": "2026-03-02",
            "note": "groceries",
        },
    ).status_code == 201
    debt_created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Иван",
            "direction": "lend",
            "principal": "50.00",
            "currency": "BYN",
            "start_date": "2026-03-03",
        },
    )
    assert debt_created.status_code == 201, debt_created.text
    debt_id = debt_created.json()["id"]
    assert client.post(
        f"/api/v1/debts/{debt_id}/repayments",
        json={"amount": "20.00", "repayment_date": "2026-03-04"},
    ).status_code == 201
    assert client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "10",
            "unit_price": "3.00",
            "fee": "1.00",
            "trade_date": "2026-03-05",
        },
    ).status_code == 201

    response = client.get(
        "/api/v1/dashboard/analytics/trend",
        params={
            "period": "custom",
            "date_from": "2026-03-01",
            "date_to": "2026-03-05",
            "granularity": "day",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["balance"] == "180.00"
    assert payload["debt_cashflow_total"] == "-30.00"
    assert payload["fx_cashflow_total"] == "-31.00"
    assert payload["cashflow_total"] == "119.00"
    assert payload["cashflow_change_pct"] is None

    day_03 = next(item for item in payload["points"] if item["bucket_start"] == "2026-03-03")
    day_04 = next(item for item in payload["points"] if item["bucket_start"] == "2026-03-04")
    day_05 = next(item for item in payload["points"] if item["bucket_start"] == "2026-03-05")
    assert day_03["cashflow_total"] == "-50.00"
    assert day_03["debt_cashflow_total"] == "-50.00"
    assert day_04["cashflow_total"] == "20.00"
    assert day_04["debt_cashflow_total"] == "20.00"
    assert day_05["cashflow_total"] == "-31.00"
    assert day_05["fx_cashflow_total"] == "-31.00"


def test_dashboard_analytics_trend_cache_is_invalidated_after_operation_mutation(client: TestClient):
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "30.00",
            "operation_date": "2026-03-02",
            "note": "trend-cache-op",
        },
    )
    assert created.status_code == 201
    operation_id = created.json()["id"]

    initial = client.get(
        "/api/v1/dashboard/analytics/trend",
        params={
            "period": "custom",
            "date_from": "2026-03-01",
            "date_to": "2026-03-03",
            "granularity": "day",
        },
    )
    assert initial.status_code == 200
    assert initial.json()["expense_total"] == "30.00"

    warm = client.get(
        "/api/v1/dashboard/analytics/trend",
        params={
            "period": "custom",
            "date_from": "2026-03-01",
            "date_to": "2026-03-03",
            "granularity": "day",
        },
    )
    assert warm.status_code == 200
    assert warm.json()["expense_total"] == "30.00"

    updated = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"amount": "90.00"},
    )
    assert updated.status_code == 200

    after_update = client.get(
        "/api/v1/dashboard/analytics/trend",
        params={
            "period": "custom",
            "date_from": "2026-03-01",
            "date_to": "2026-03-03",
            "granularity": "day",
        },
    )
    assert after_update.status_code == 200
    assert after_update.json()["expense_total"] == "90.00"


def test_dashboard_analytics_calendar_year_returns_month_cells(client: TestClient):
    client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "100.00",
            "operation_date": "2026-01-05",
            "note": "jan",
        },
    )
    client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "40.00",
            "operation_date": "2026-03-10",
            "note": "mar",
        },
    )

    response = client.get("/api/v1/dashboard/analytics/calendar/year", params={"year": 2026})
    assert response.status_code == 200
    payload = response.json()
    assert payload["year"] == 2026
    assert payload["income_total"] == "100.00"
    assert payload["expense_total"] == "40.00"
    assert payload["operations_count"] == 2
    assert len(payload["months"]) == 12
    jan = next(item for item in payload["months"] if item["month"] == "2026-01")
    mar = next(item for item in payload["months"] if item["month"] == "2026-03")
    assert jan["income_total"] == "100.00"
    assert mar["expense_total"] == "40.00"


def test_dashboard_analytics_calendar_year_includes_cashflow_overlays(client: TestClient):
    debt_created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Nina",
            "direction": "borrow",
            "principal": "90.00",
            "currency": "BYN",
            "start_date": "2026-01-10",
            "note": "borrowed",
        },
    )
    assert debt_created.status_code == 201
    debt_id = debt_created.json()["id"]

    repaid = client.post(
        f"/api/v1/debts/{debt_id}/repayments",
        json={
            "amount": "30.00",
            "repayment_date": "2026-02-10",
            "note": "repay",
        },
    )
    assert repaid.status_code == 201

    fx_trade = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "sell",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "5",
            "unit_price": "3.20",
            "fee": "1.00",
            "trade_date": "2026-02-15",
            "note": "usd-sell",
        },
    )
    assert fx_trade.status_code == 400

    buy_trade = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "5",
            "unit_price": "3.00",
            "fee": "0.00",
            "trade_date": "2026-01-12",
            "note": "usd-buy",
        },
    )
    assert buy_trade.status_code == 201
    sell_trade = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "sell",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "5",
            "unit_price": "3.20",
            "fee": "1.00",
            "trade_date": "2026-02-15",
            "note": "usd-sell",
        },
    )
    assert sell_trade.status_code == 201

    response = client.get("/api/v1/dashboard/analytics/calendar/year", params={"year": 2026})
    assert response.status_code == 200
    payload = response.json()
    jan = next(item for item in payload["months"] if item["month"] == "2026-01")
    feb = next(item for item in payload["months"] if item["month"] == "2026-02")

    assert jan["debt_cashflow_total"] == "90.00"
    assert jan["fx_cashflow_total"] == "-15.00"
    assert jan["cashflow_total"] == "75.00"

    assert feb["debt_cashflow_total"] == "-30.00"
    assert feb["fx_cashflow_total"] == "15.00"
    assert feb["cashflow_total"] == "-15.00"


def test_dashboard_analytics_calendar_year_cache_is_invalidated_after_operation_mutation(client: TestClient):
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "40.00",
            "operation_date": "2026-03-10",
            "note": "calendar-year-cache-op",
        },
    )
    assert created.status_code == 201
    operation_id = created.json()["id"]

    initial = client.get("/api/v1/dashboard/analytics/calendar/year", params={"year": 2026})
    assert initial.status_code == 200
    assert initial.json()["expense_total"] == "40.00"

    warm = client.get("/api/v1/dashboard/analytics/calendar/year", params={"year": 2026})
    assert warm.status_code == 200
    assert warm.json()["expense_total"] == "40.00"

    updated = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"amount": "90.00"},
    )
    assert updated.status_code == 200

    after_update = client.get("/api/v1/dashboard/analytics/calendar/year", params={"year": 2026})
    assert after_update.status_code == 200
    assert after_update.json()["expense_total"] == "90.00"


def test_dashboard_analytics_highlights_returns_kpis_and_top_blocks(client: TestClient):
    previous_month = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "40.00",
            "operation_date": "2026-02-10",
            "note": "prev-month",
            "receipt_items": [
                {"shop_name": "Store", "name": "Milk", "quantity": "1", "unit_price": "2.00"},
            ],
        },
    )
    assert previous_month.status_code == 201

    first = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "120.00",
            "operation_date": "2026-03-10",
            "note": "big-expense",
            "receipt_items": [
                {"shop_name": "Store", "name": "Milk", "quantity": "1", "unit_price": "2.40"},
                {"shop_name": "Store", "name": "Steak", "quantity": "1", "unit_price": "25.00"},
            ],
        },
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "300.00",
            "operation_date": "2026-03-11",
            "note": "salary",
        },
    )
    assert second.status_code == 201

    response = client.get("/api/v1/dashboard/analytics/highlights", params={"month": "2026-03"})
    assert response.status_code == 200
    payload = response.json()

    assert payload["period"] == "month"
    assert payload["category_breakdown_kind"] == "expense"
    assert payload["date_from"] == "2026-03-01"
    assert payload["date_to"] == "2026-03-31"
    assert payload["month"] == "2026-03"
    assert payload["income_total"] == "300.00"
    assert payload["expense_total"] == "120.00"
    assert payload["surplus_total"] == "180.00"
    assert payload["deficit_total"] == "0"
    assert payload["operations_count"] == 2
    assert payload["max_expense_day_date"] == "2026-03-10"
    assert payload["max_expense_day_total"] == "120.00"
    assert len(payload["top_operations"]) == 1
    assert payload["top_operations"][0]["amount"] == "120.00"
    assert len(payload["top_categories"]) == 1
    assert payload["top_categories"][0]["total_expense"] == "120.00"
    assert payload["category_breakdown"][0]["total_amount"] == "120.00"
    assert len(payload["anomalies"]) == 0
    assert len(payload["top_positions"]) >= 2
    assert payload["top_positions"][0]["name"] == "Steak"
    assert any(item["name"] == "Milk" for item in payload["price_increases"])


def test_dashboard_analytics_highlights_includes_fx_cashflow_for_period(client: TestClient):
    income = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "300.00",
            "operation_date": "2026-03-11",
            "note": "salary",
        },
    )
    assert income.status_code == 201
    expense = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "120.00",
            "operation_date": "2026-03-12",
            "note": "groceries",
        },
    )
    assert expense.status_code == 201

    buy_trade = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "50",
            "unit_price": "3.10",
            "fee": "0",
            "trade_date": "2026-03-14",
            "note": "buy usd",
        },
    )
    assert buy_trade.status_code == 201
    sell_trade = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "sell",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "10",
            "unit_price": "3.25",
            "fee": "0",
            "trade_date": "2026-03-20",
            "note": "sell usd",
        },
    )
    assert sell_trade.status_code == 201

    response = client.get("/api/v1/dashboard/analytics/highlights", params={"month": "2026-03"})
    assert response.status_code == 200
    payload = response.json()

    assert payload["income_total"] == "300.00"
    assert payload["expense_total"] == "120.00"
    assert payload["balance"] == "180.00"
    assert payload["cashflow_total"] == "57.50"
    assert payload["fx_cashflow_total"] == "-122.50"
    assert payload["prev_fx_cashflow_total"] in ("0", "0.00")
    assert payload["fx_cashflow_change_pct"] is None


def test_dashboard_summary_and_highlights_use_unified_cashflow(client: TestClient):
    assert client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "300.00",
            "operation_date": "2026-03-11",
            "note": "salary",
        },
    ).status_code == 201
    assert client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "120.00",
            "operation_date": "2026-03-12",
            "note": "groceries",
        },
    ).status_code == 201
    debt_created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Иван",
            "direction": "lend",
            "principal": "50.00",
            "start_date": "2026-03-13",
        },
    )
    assert debt_created.status_code == 201, debt_created.text
    debt_id = debt_created.json()["id"]
    assert client.post(
        f"/api/v1/debts/{debt_id}/repayments",
        json={"amount": "20.00", "repayment_date": "2026-03-15"},
    ).status_code == 201
    assert client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "10",
            "unit_price": "3.00",
            "fee": "1.00",
            "trade_date": "2026-03-16",
        },
    ).status_code == 201

    summary = client.get(
        "/api/v1/dashboard/summary",
        params={"period": "custom", "date_from": "2026-03-01", "date_to": "2026-03-31"},
    )
    assert summary.status_code == 200, summary.text
    summary_payload = summary.json()
    assert summary_payload["balance"] == "180.00"
    assert summary_payload["debt_cashflow_total"] == "-30.00"
    assert summary_payload["fx_cashflow_total"] == "-31.00"
    assert summary_payload["cashflow_total"] == "119.00"

    highlights = client.get("/api/v1/dashboard/analytics/highlights", params={"month": "2026-03"})
    assert highlights.status_code == 200, highlights.text
    payload = highlights.json()
    assert payload["balance"] == "180.00"
    assert payload["debt_cashflow_total"] == "-30.00"
    assert payload["fx_cashflow_total"] == "-31.00"
    assert payload["cashflow_total"] == "119.00"
    assert payload["surplus_total"] == "119.00"
    assert payload["deficit_total"] in ("0", "0.00")


def test_dashboard_analytics_highlights_accepts_day_period(client: TestClient):
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "75.00",
            "operation_date": "2026-03-11",
            "note": "day-period",
        },
    )
    assert created.status_code == 201

    response = client.get(
        "/api/v1/dashboard/analytics/highlights",
        params={"period": "day", "date_to": "2026-03-11"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "day"
    assert payload["date_from"] == "2026-03-11"
    assert payload["date_to"] == "2026-03-11"
    assert payload["expense_total"] == "75.00"


def test_dashboard_analytics_highlights_category_breakdown_respects_kind_filter(client: TestClient):
    food = client.post(
        "/api/v1/categories",
        json={"name": "Еда", "kind": "expense"},
    )
    salary = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата", "kind": "income"},
    )
    assert food.status_code == 200
    assert salary.status_code == 200

    expense = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "category_id": food.json()["id"],
            "amount": "120.00",
            "operation_date": "2026-03-10",
        },
    )
    income = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "category_id": salary.json()["id"],
            "amount": "300.00",
            "operation_date": "2026-03-11",
        },
    )
    assert expense.status_code == 201
    assert income.status_code == 201

    income_breakdown = client.get(
        "/api/v1/dashboard/analytics/highlights",
        params={"month": "2026-03", "category_kind": "income"},
    )
    assert income_breakdown.status_code == 200
    income_payload = income_breakdown.json()
    assert income_payload["category_breakdown_kind"] == "income"
    assert len(income_payload["category_breakdown"]) == 1


def test_dashboard_analytics_highlights_uses_receipt_item_categories_for_structure(client: TestClient):
    food = client.post("/api/v1/categories", json={"name": "Еда", "kind": "expense"})
    transport = client.post("/api/v1/categories", json={"name": "Транспорт", "kind": "expense"})
    misc = client.post("/api/v1/categories", json={"name": "Прочее", "kind": "expense"})
    assert food.status_code == 200
    assert transport.status_code == 200
    assert misc.status_code == 200

    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "category_id": misc.json()["id"],
            "amount": "120.00",
            "operation_date": "2026-03-12",
            "note": "mixed receipt",
            "receipt_items": [
                {
                    "name": "Обед",
                    "quantity": "1",
                    "unit_price": "30.00",
                    "category_id": food.json()["id"],
                },
                {
                    "name": "Такси",
                    "quantity": "1",
                    "unit_price": "70.00",
                    "category_id": transport.json()["id"],
                },
            ],
        },
    )
    assert created.status_code == 201

    response = client.get("/api/v1/dashboard/analytics/highlights", params={"month": "2026-03"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["expense_total"] == "120.00"
    breakdown = {item["category_name"]: item for item in payload["category_breakdown"]}
    assert breakdown["Транспорт"]["total_amount"] == "70.00"
    assert breakdown["Еда"]["total_amount"] == "30.00"
    assert breakdown["Прочее"]["total_amount"] == "20.00"


def test_dashboard_analytics_highlights_preserve_mixed_receipt_categories_with_linked_fx_settlement(client: TestClient):
    food = client.post("/api/v1/categories", json={"name": "Продукты", "kind": "expense"})
    snacks = client.post("/api/v1/categories", json={"name": "Снэки", "kind": "expense"})
    misc = client.post("/api/v1/categories", json={"name": "Прочее", "kind": "expense"})
    assert food.status_code == 200
    assert snacks.status_code == 200
    assert misc.status_code == 200

    funding = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "quantity": "50.00",
            "unit_price": "3.20",
            "fee": "0.00",
            "trade_date": "2026-03-01",
        },
    )
    assert funding.status_code == 201, funding.text

    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "category_id": misc.json()["id"],
            "amount": "21.30",
            "operation_date": "2026-04-01",
            "receipt_items": [
                {
                    "shop_name": "Евроопт",
                    "name": "Перец желтый 1кг",
                    "quantity": "0.18",
                    "unit_price": "16.33",
                    "category_id": food.json()["id"],
                },
                {
                    "shop_name": "Евроопт",
                    "name": "Сырок какао",
                    "quantity": "4",
                    "unit_price": "0.95",
                    "category_id": snacks.json()["id"],
                },
            ],
            "fx_settlement": {
                "asset_currency": "USD",
                "quantity": "7.42",
                "quote_total": "21.30",
                "unit_price": "2.870620",
            },
        },
    )
    assert created.status_code == 201, created.text

    response = client.get(
        "/api/v1/dashboard/analytics/highlights",
        params={"period": "custom", "date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    breakdown = {item["category_name"]: item for item in payload["category_breakdown"]}
    assert breakdown["Продукты"]["total_amount"] == "2.94"
    assert breakdown["Снэки"]["total_amount"] == "3.80"
    assert breakdown["Прочее"]["total_amount"] == "14.56"


def test_dashboard_analytics_ignores_category_statistics_flag(client: TestClient):
    hidden = client.post(
        "/api/v1/categories",
        json={"name": "Скрытая", "kind": "expense", "include_in_statistics": False},
    )
    visible = client.post(
        "/api/v1/categories",
        json={"name": "Видимая", "kind": "expense"},
    )
    assert hidden.status_code == 200
    assert visible.status_code == 200

    hidden_op = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "category_id": hidden.json()["id"],
            "amount": "200.00",
            "operation_date": "2026-03-10",
        },
    )
    visible_op = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "category_id": visible.json()["id"],
            "amount": "120.00",
            "operation_date": "2026-03-11",
        },
    )
    assert hidden_op.status_code == 201
    assert visible_op.status_code == 201

    summary = client.get(
        "/api/v1/dashboard/summary",
        params={"period": "custom", "date_from": "2026-03-01", "date_to": "2026-03-31"},
    )
    assert summary.status_code == 200
    assert summary.json()["expense_total"] == "320.00"

    highlights = client.get("/api/v1/dashboard/analytics/highlights", params={"month": "2026-03"})
    assert highlights.status_code == 200
    payload = highlights.json()
    assert payload["expense_total"] == "320.00"
    assert len(payload["category_breakdown"]) == 2
    assert {item["category_name"] for item in payload["category_breakdown"]} == {"Скрытая", "Видимая"}

    all_breakdown = client.get(
        "/api/v1/dashboard/analytics/highlights",
        params={"month": "2026-03", "category_kind": "all"},
    )
    assert all_breakdown.status_code == 200
    all_payload = all_breakdown.json()
    assert all_payload["category_breakdown_kind"] == "all"
    assert len(all_payload["category_breakdown"]) == 2
    assert {item["category_name"] for item in all_payload["category_breakdown"]} == {"Скрытая", "Видимая"}


def test_dashboard_analytics_highlights_can_group_breakdown_by_category_group(client: TestClient):
    food_group = client.post(
        "/api/v1/categories/groups",
        json={"name": "Еда", "kind": "expense"},
    )
    snacks = client.post(
        "/api/v1/categories",
        json={"name": "Снеки", "kind": "expense", "group_id": food_group.json()["id"]},
    )
    groceries = client.post(
        "/api/v1/categories",
        json={"name": "Продукты", "kind": "expense", "group_id": food_group.json()["id"]},
    )
    transport = client.post(
        "/api/v1/categories",
        json={"name": "Транспорт", "kind": "expense"},
    )
    assert food_group.status_code == 200
    assert snacks.status_code == 200
    assert groceries.status_code == 200
    assert transport.status_code == 200

    for payload in (
        {
            "kind": "expense",
            "category_id": snacks.json()["id"],
            "amount": "40.00",
            "operation_date": "2026-03-10",
        },
        {
            "kind": "expense",
            "category_id": groceries.json()["id"],
            "amount": "60.00",
            "operation_date": "2026-03-11",
        },
        {
            "kind": "expense",
            "category_id": transport.json()["id"],
            "amount": "25.00",
            "operation_date": "2026-03-12",
        },
    ):
        response = client.post("/api/v1/operations", json=payload)
        assert response.status_code == 201

    grouped = client.get(
        "/api/v1/dashboard/analytics/highlights",
        params={"month": "2026-03", "category_breakdown_level": "group"},
    )
    assert grouped.status_code == 200
    payload = grouped.json()
    assert payload["category_breakdown_level"] == "group"
    assert len(payload["category_breakdown"]) == 2
    assert payload["category_breakdown"][0]["category_name"] == "Еда"
    assert payload["category_breakdown"][0]["group_name"] == "Еда"
    assert payload["category_breakdown"][0]["category_id"] is None
    assert payload["category_breakdown"][0]["total_amount"] == "100.00"
    assert payload["category_breakdown"][1]["category_name"] == "Без группы"
    assert payload["category_breakdown"][1]["group_id"] is None
    assert payload["category_breakdown"][1]["total_amount"] == "25.00"


def test_dashboard_analytics_highlights_cache_is_invalidated_after_operation_mutation(client: TestClient):
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "100.00",
            "operation_date": "2026-03-10",
            "note": "analytics-cache-op",
        },
    )
    assert created.status_code == 201
    operation_id = created.json()["id"]

    initial = client.get("/api/v1/dashboard/analytics/highlights", params={"month": "2026-03"})
    assert initial.status_code == 200
    assert initial.json()["expense_total"] == "100.00"

    warm = client.get("/api/v1/dashboard/analytics/highlights", params={"month": "2026-03"})
    assert warm.status_code == 200
    assert warm.json()["expense_total"] == "100.00"

    updated = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"amount": "250.00"},
    )
    assert updated.status_code == 200

    after_update = client.get("/api/v1/dashboard/analytics/highlights", params={"month": "2026-03"})
    assert after_update.status_code == 200
    assert after_update.json()["expense_total"] == "250.00"


def test_dashboard_analytics_highlights_cache_is_invalidated_after_category_mutation(client: TestClient):
    group = client.post(
        "/api/v1/categories/groups",
        json={"name": "Старое имя", "kind": "expense"},
    )
    assert group.status_code == 200
    category = client.post(
        "/api/v1/categories",
        json={"name": "Продукты", "kind": "expense", "group_id": group.json()["id"]},
    )
    assert category.status_code == 200
    op = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "category_id": category.json()["id"],
            "amount": "80.00",
            "operation_date": "2026-03-12",
        },
    )
    assert op.status_code == 201

    initial = client.get(
        "/api/v1/dashboard/analytics/highlights",
        params={"month": "2026-03", "category_breakdown_level": "group"},
    )
    assert initial.status_code == 200
    assert initial.json()["category_breakdown"][0]["group_name"] == "Старое имя"

    renamed = client.patch(
        f"/api/v1/categories/groups/{group.json()['id']}",
        json={"name": "Новое имя"},
    )
    assert renamed.status_code == 200

    after_update = client.get(
        "/api/v1/dashboard/analytics/highlights",
        params={"month": "2026-03", "category_breakdown_level": "group"},
    )
    assert after_update.status_code == 200
    assert after_update.json()["category_breakdown"][0]["group_name"] == "Новое имя"
