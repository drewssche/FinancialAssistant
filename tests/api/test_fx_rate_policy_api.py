from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import ActivityEvent
from app.db.session import get_db
from app.main import app
from app.repositories.currency_repo import CurrencyRepository
from app.services.bank_currency_rate_refresh_service import BankCurrencyRateRefreshService
from app.services.work_service import WorkService
from tests.api.test_operations_api import _client_lifecycle


@pytest.fixture
def client():
    yield from _client_lifecycle()


def _bank_quote(*, currency: str, buy: str, sell: str, scale: int = 1):
    quoted_at = datetime(2026, 8, 19, 10, 0, tzinfo=timezone.utc)
    return SimpleNamespace(
        bank_code="technobank",
        bank_name="Технобанк",
        currency=currency,
        base_currency="BYN",
        scale=scale,
        buy_rate=Decimal(buy),
        sell_rate=Decimal(sell),
        channel="cash",
        location_name="Минск",
        quoted_at=quoted_at,
        fetched_at=quoted_at,
    )


def test_bank_operation_freezes_quote_for_regular_and_unchanged_policy_updates(
    client: TestClient,
    monkeypatch,
):
    state = {"quote": _bank_quote(currency="EUR", buy="3.49", sell="3.53"), "calls": 0}

    def get_bank_rate(_repo, **_kwargs):
        state["calls"] += 1
        return state["quote"]

    monkeypatch.setattr(CurrencyRepository, "get_bank_rate", get_bank_rate)
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "229.00",
            "currency": "EUR",
            "fx_rate_source": "bank",
            "fx_bank_code": "technobank",
            "fx_bank_channel": "cash",
            "fx_rate_kind": "sell",
            "fx_payment_mode": "direct_conversion",
            "operation_date": "2026-08-19",
            "note": "Подписка",
        },
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    operation_id = payload["id"]
    assert payload["amount"] == "808.37"
    assert payload["fx_rate"] == "3.530000"
    assert payload["fx_rate_display"] == "3.530000"
    assert payload["fx_bank_name"] == "Технобанк"
    assert payload["fx_payment_mode"] == "direct_conversion"
    assert payload["fx_settlement"] is None
    assert state["calls"] == 1

    state["quote"] = _bank_quote(currency="EUR", buy="3.95", sell="4.00")
    unchanged = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={
            "note": "Подписка для работы",
            "fx_rate": "3.530000",
            "fx_rate_source": "bank",
            "fx_bank_code": "technobank",
            "fx_bank_channel": "cash",
            "fx_rate_kind": "sell",
            "fx_payment_mode": "direct_conversion",
        },
    )
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json()["amount"] == "808.37"
    assert unchanged.json()["fx_rate"] == "3.530000"
    assert state["calls"] == 1

    amount_only = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={
            "amount": "230.00",
            "fx_rate": "3.530000",
            "fx_rate_source": "bank",
            "fx_bank_code": "technobank",
            "fx_bank_channel": "cash",
            "fx_rate_kind": "sell",
            "fx_payment_mode": "direct_conversion",
        },
    )
    assert amount_only.status_code == 200, amount_only.text
    assert amount_only.json()["amount"] == "811.90"
    assert amount_only.json()["fx_rate"] == "3.530000"
    assert state["calls"] == 1

    refreshed = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"fx_refresh_rate": True},
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["fx_rate"] == "4.000000"
    assert refreshed.json()["amount"] == "920.00"
    assert state["calls"] == 2


def test_manual_rub_quote_is_displayed_per_100_but_calculated_per_one(client: TestClient):
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "1000.00",
            "currency": "RUB",
            "fx_rate_source": "manual",
            "fx_manual_rate": "3.56",
            "fx_payment_mode": "direct_conversion",
            "operation_date": "2026-08-19",
        },
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["fx_rate"] == "0.035600"
    assert payload["fx_rate_scale"] == 100
    assert payload["fx_rate_display"] == "3.560000"
    assert payload["amount"] == "35.60"


def test_nbrb_operation_uses_historical_or_previous_workday_rate_and_ignores_manual_rows(
    client: TestClient,
):
    for rate_date, rate, source in (
        ("2026-08-14", "3.10", "nbrb_history_unit"),
        ("2026-08-17", "3.20", "nbrb_history_unit"),
        ("2026-08-18", "9.99", "manual"),
    ):
        response = client.put(
            "/api/v1/currency/rates/current",
            json={
                "currency": "EUR",
                "rate": rate,
                "rate_date": rate_date,
                "source": source,
            },
        )
        assert response.status_code == 200, response.text

    weekend = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "10.00",
            "currency": "EUR",
            "fx_rate_source": "nbrb",
            "fx_payment_mode": "direct_conversion",
            "operation_date": "2026-08-16",
        },
    )
    assert weekend.status_code == 201, weekend.text
    assert weekend.json()["fx_rate"] == "3.100000"
    assert weekend.json()["fx_rate_date"] == "2026-08-14"
    assert weekend.json()["amount"] == "31.00"

    exact = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "10.00",
            "currency": "EUR",
            "fx_rate_source": "nbrb",
            "fx_payment_mode": "direct_conversion",
            "operation_date": "2026-08-17",
        },
    )
    assert exact.status_code == 201, exact.text
    assert exact.json()["fx_rate"] == "3.200000"
    assert exact.json()["fx_rate_date"] == "2026-08-17"

    options = client.get(
        "/api/v1/currency/rate-options",
        params={"currency": "EUR", "base_currency": "BYN"},
    )
    assert options.status_code == 200, options.text
    assert options.json()["nbrb_rate"]["unit_rate"] == "3.200000"
    assert options.json()["nbrb_rate"]["source"] == "nbrb_history_unit"

    weekend_options = client.get(
        "/api/v1/currency/rate-options",
        params={
            "currency": "EUR",
            "base_currency": "BYN",
            "as_of": "2026-08-16",
        },
    )
    assert weekend_options.status_code == 200, weekend_options.text
    assert weekend_options.json()["nbrb_rate"]["unit_rate"] == "3.100000"
    assert weekend_options.json()["nbrb_rate"]["rate_date"] == "2026-08-14"


def test_bank_buy_rub_scale_and_stale_provenance_are_snapshotted(
    client: TestClient,
    monkeypatch,
):
    stale_quote = _bank_quote(currency="RUB", buy="3.40", sell="3.56", scale=100)
    stale_quote.fetched_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    stale_quote.quoted_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(
        CurrencyRepository,
        "get_bank_rate",
        lambda _repo, **_kwargs: stale_quote,
    )
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "1000.00",
            "currency": "RUB",
            "fx_rate_source": "bank",
            "fx_bank_code": "technobank",
            "fx_bank_channel": "cash",
            "fx_rate_kind": "buy",
            "fx_payment_mode": "direct_conversion",
            "operation_date": "2026-08-19",
        },
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["fx_rate"] == "0.034000"
    assert payload["fx_rate_display"] == "3.400000"
    assert payload["fx_rate_scale"] == 100
    assert payload["fx_rate_kind"] == "buy"
    assert payload["fx_rate_stale"] is True
    assert payload["amount"] == "34.00"


def test_bank_plan_is_dynamic_but_confirmation_and_history_keep_snapshot(
    client: TestClient,
    monkeypatch,
):
    state = {"quote": _bank_quote(currency="EUR", buy="3.49", sell="3.53")}
    monkeypatch.setattr(
        CurrencyRepository,
        "get_bank_rate",
        lambda _repo, **_kwargs: state["quote"],
    )
    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "229.00",
            "currency": "EUR",
            "scheduled_date": "2026-09-03",
            "fx_rate_source": "bank",
            "fx_bank_code": "technobank",
            "fx_bank_channel": "cash",
            "fx_rate_kind": "sell",
            "fx_payment_mode": "direct_conversion",
            "note": "Подписка",
        },
    )
    assert created.status_code == 201, created.text
    plan_id = created.json()["id"]
    assert created.json()["current_rate"] == "3.530000"
    assert created.json()["current_base_amount"] == "808.37"

    state["quote"] = _bank_quote(currency="EUR", buy="3.55", sell="3.60")
    confirmed = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    operation = confirmed.json()["operation"]
    assert operation["amount"] == "824.40"
    assert operation["fx_rate"] == "3.600000"
    assert operation["fx_bank_code"] == "technobank"

    state["quote"] = _bank_quote(currency="EUR", buy="3.65", sell="3.70")
    history = client.get("/api/v1/plans/history")
    assert history.status_code == 200, history.text
    event = history.json()["items"][0]
    assert event["original_amount"] == "229.00"
    assert event["currency"] == "EUR"
    assert event["amount"] == "824.40"
    assert event["fx_rate"] == "3.600000"
    assert event["fx_rate_display"] == "3.600000"
    assert event["fx_bank_name"] == "Технобанк"


def test_foreign_balance_plan_confirmation_creates_one_linked_settlement_and_rolls_back_shortage(
    client: TestClient,
):
    funded = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "EUR",
            "quote_currency": "BYN",
            "quantity": "300.00",
            "unit_price": "3.50",
            "fee": "0",
            "trade_date": "2026-08-19",
        },
    )
    assert funded.status_code == 201, funded.text
    plan = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "229.00",
            "currency": "EUR",
            "scheduled_date": "2026-08-19",
            "fx_rate_source": "manual",
            "fx_manual_rate": "3.50",
            "fx_payment_mode": "foreign_balance",
        },
    )
    assert plan.status_code == 201, plan.text
    confirmed = client.post(f"/api/v1/plans/{plan.json()['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    operation = confirmed.json()["operation"]
    assert operation["fx_settlement"]["quantity"] == "229.000"
    assert operation["fx_settlement"]["trade_id"]
    overview = client.get("/api/v1/currency/overview", params={"currency": "EUR"})
    assert overview.status_code == 200, overview.text
    assert overview.json()["positions"][0]["quantity"] == "71.000000"

    insufficient = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "100.00",
            "currency": "EUR",
            "scheduled_date": "2026-08-20",
            "fx_rate_source": "manual",
            "fx_manual_rate": "3.50",
            "fx_payment_mode": "foreign_balance",
        },
    )
    assert insufficient.status_code == 201, insufficient.text
    rejected = client.post(f"/api/v1/plans/{insufficient.json()['id']}/confirm")
    assert rejected.status_code == 400, rejected.text
    assert "Not enough currency balance" in rejected.json()["detail"]
    fetched_plan = client.get(f"/api/v1/plans/{insufficient.json()['id']}")
    assert fetched_plan.status_code == 200
    assert fetched_plan.json()["confirm_count"] == 0
    operations = client.get("/api/v1/operations", params={"page": 1, "page_size": 20})
    assert operations.json()["total"] == 1


def test_operation_payment_mode_transitions_create_remove_and_revalidate_settlement(client: TestClient):
    funded = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "EUR",
            "quote_currency": "BYN",
            "quantity": "50.00",
            "unit_price": "3.50",
            "fee": "0",
            "trade_date": "2026-08-01",
        },
    )
    assert funded.status_code == 201, funded.text
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "10.00",
            "currency": "EUR",
            "fx_rate_source": "manual",
            "fx_manual_rate": "3.50",
            "fx_payment_mode": "foreign_balance",
            "operation_date": "2026-08-19",
        },
    )
    assert created.status_code == 201, created.text
    operation_id = created.json()["id"]

    direct = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"fx_payment_mode": "direct_conversion"},
    )
    assert direct.status_code == 200, direct.text
    assert direct.json()["fx_settlement"] is None
    assert client.get("/api/v1/currency/overview", params={"currency": "EUR"}).json()["positions"][0]["quantity"] == "50.000000"

    balance = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"fx_payment_mode": "foreign_balance"},
    )
    assert balance.status_code == 200, balance.text
    assert balance.json()["fx_settlement"]["quantity"] == "10.000"
    assert client.get("/api/v1/currency/overview", params={"currency": "EUR"}).json()["positions"][0]["quantity"] == "40.000000"
    assert balance.json()["fx_settlement"]["trade_id"]

    rejected = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"amount": "60.00"},
    )
    assert rejected.status_code == 400
    assert "Not enough currency balance" in rejected.json()["detail"]
    unchanged = client.get(f"/api/v1/operations/{operation_id}")
    assert unchanged.json()["original_amount"] == "10.00"
    assert unchanged.json()["fx_settlement"]["quantity"] == "10.000"


def test_delete_restore_preserves_bank_provenance_and_revalidates_linked_trade(
    client: TestClient,
    monkeypatch,
):
    quote = _bank_quote(currency="EUR", buy="3.49", sell="3.53")
    monkeypatch.setattr(CurrencyRepository, "get_bank_rate", lambda _repo, **_kwargs: quote)
    assert client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "EUR",
            "quote_currency": "BYN",
            "quantity": "20.00",
            "unit_price": "3.40",
            "fee": "0",
            "trade_date": "2026-08-01",
        },
    ).status_code == 201
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "10.00",
            "currency": "EUR",
            "fx_rate_source": "bank",
            "fx_bank_code": "technobank",
            "fx_bank_channel": "cash",
            "fx_rate_kind": "sell",
            "fx_payment_mode": "foreign_balance",
            "operation_date": "2026-08-19",
        },
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    operation_id = payload["id"]
    trade_id = payload["fx_settlement"]["trade_id"]
    assert client.delete(f"/api/v1/operations/{operation_id}").status_code == 204
    restored = client.post(f"/api/v1/operations/{operation_id}/restore")
    assert restored.status_code == 200, restored.text
    restored_payload = restored.json()
    assert restored_payload["fx_rate"] == "3.530000"
    assert restored_payload["fx_rate_source"] == "bank"
    assert restored_payload["fx_bank_name"] == "Технобанк"
    assert restored_payload["fx_bank_channel"] == "cash"
    assert restored_payload["fx_rate_kind"] == "sell"
    assert restored_payload["fx_settlement"]["trade_id"] == trade_id


def test_legacy_v1_restore_infers_rub_scale_and_foreign_balance_mode(client: TestClient):
    funded = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "RUB",
            "quote_currency": "BYN",
            "quantity": "1000.00",
            "unit_price": "0.0356",
            "fee": "0",
            "trade_date": "2026-08-01",
        },
    )
    assert funded.status_code == 201, funded.text
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "100.00",
            "currency": "RUB",
            "fx_rate_source": "manual",
            "fx_manual_rate": "3.56",
            "fx_payment_mode": "foreign_balance",
            "operation_date": "2026-08-19",
        },
    )
    assert created.status_code == 201, created.text
    operation_id = created.json()["id"]
    trade_id = created.json()["fx_settlement"]["trade_id"]
    assert client.delete(f"/api/v1/operations/{operation_id}").status_code == 204

    override = app.dependency_overrides[get_db]
    session_generator = override()
    db = next(session_generator)
    try:
        event = db.scalar(
            select(ActivityEvent)
            .where(
                ActivityEvent.user_id == 1,
                ActivityEvent.entity_type == "operation",
                ActivityEvent.entity_id == operation_id,
                ActivityEvent.event_type == "deleted",
            )
            .order_by(ActivityEvent.id.desc())
        )
        assert event is not None
        metadata = dict(event.metadata_json or {})
        restore_snapshot = dict(metadata["_restore_snapshot"])
        restore_snapshot["version"] = 1
        operation_snapshot = dict(restore_snapshot["operation"])
        for key in (
            "fx_rate_source",
            "fx_bank_code",
            "fx_bank_name",
            "fx_bank_channel",
            "fx_rate_kind",
            "fx_rate_scale",
            "fx_rate_date",
            "fx_quoted_at",
            "fx_fetched_at",
            "fx_rate_stale",
            "fx_payment_mode",
        ):
            operation_snapshot.pop(key, None)
        restore_snapshot["operation"] = operation_snapshot
        metadata["_restore_snapshot"] = restore_snapshot
        event.metadata_json = metadata
        db.commit()
    finally:
        session_generator.close()

    restored = client.post(f"/api/v1/operations/{operation_id}/restore")
    assert restored.status_code == 200, restored.text
    payload = restored.json()
    assert payload["fx_rate"] == "0.035600"
    assert payload["fx_rate_scale"] == 100
    assert payload["fx_rate_display"] == "3.560000"
    assert payload["fx_payment_mode"] == "foreign_balance"
    assert payload["fx_settlement"]["trade_id"] == trade_id


def test_plan_confirm_rolls_back_operation_event_and_counter_on_late_failure(
    client: TestClient,
    monkeypatch,
):
    plan = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "10.00",
            "scheduled_date": "2026-08-19",
        },
    )
    assert plan.status_code == 201
    plan_id = plan.json()["id"]
    monkeypatch.setattr(
        WorkService,
        "link_confirmed_plan_payment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("injected late failure")),
    )
    with pytest.raises(RuntimeError, match="injected late failure"):
        client.post(f"/api/v1/plans/{plan_id}/confirm")
    operations = client.get("/api/v1/operations", params={"page": 1, "page_size": 20})
    assert operations.json()["total"] == 0
    history = client.get("/api/v1/plans/history")
    assert history.json()["total"] == 0
    fetched_plan = client.get(f"/api/v1/plans/{plan_id}")
    assert fetched_plan.json()["confirm_count"] == 0
    assert fetched_plan.json()["confirmed_operation_id"] is None


def test_bank_policy_never_falls_back_to_nbrb_and_public_trade_cannot_link_operation(
    client: TestClient,
    monkeypatch,
):
    rate = client.put(
        "/api/v1/currency/rates/current",
        json={
            "currency": "EUR",
            "rate": "3.40",
            "rate_date": "2026-08-19",
            "source": "nbrb_auto_unit",
        },
    )
    assert rate.status_code == 200
    monkeypatch.setattr(CurrencyRepository, "get_bank_rate", lambda _repo, **_kwargs: None)
    rejected = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "10.00",
            "currency": "EUR",
            "fx_rate_source": "bank",
            "fx_bank_code": "technobank",
            "fx_bank_channel": "cash",
            "fx_rate_kind": "sell",
            "operation_date": "2026-08-19",
        },
    )
    assert rejected.status_code == 400
    assert "Нет курса" in rejected.json()["detail"]

    operation = client.post(
        "/api/v1/operations",
        json={"kind": "expense", "amount": "1.00", "operation_date": "2026-08-19"},
    )
    assert operation.status_code == 201
    forged_link = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "EUR",
            "quote_currency": "BYN",
            "quantity": "1.00",
            "unit_price": "3.50",
            "fee": "0",
            "linked_operation_id": operation.json()["id"],
            "trade_date": "2026-08-19",
        },
    )
    assert forged_link.status_code == 400
    assert "managed by operations" in forged_link.json()["detail"]
    forged_kind = client.post(
        "/api/v1/currency/trades",
        json={
            "side": "buy",
            "asset_currency": "EUR",
            "quote_currency": "BYN",
            "quantity": "1.00",
            "unit_price": "3.50",
            "fee": "0",
            "trade_kind": "card_payment",
            "trade_date": "2026-08-19",
        },
    )
    assert forged_kind.status_code == 400
    assert "trade_kind is managed by operations" in forged_kind.json()["detail"]


def test_rate_options_return_all_providers_regardless_dashboard_preferences(
    client: TestClient,
    monkeypatch,
):
    quote = _bank_quote(currency="EUR", buy="3.49", sell="3.53")
    monkeypatch.setattr(
        CurrencyRepository,
        "list_bank_rates",
        lambda _repo, **_kwargs: [quote],
    )
    response = client.get(
        "/api/v1/currency/rate-options",
        params={"currency": "EUR", "base_currency": "BYN"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert [item["bank_code"] for item in payload["providers"]] == [
        "priorbank",
        "technobank",
        "bsb",
        "sber",
    ]
    technobank = next(item for item in payload["bank_rates"] if item["bank_code"] == "technobank")
    assert technobank["sell_rate"] == "3.530000"
    assert technobank["sell_unit_rate"] == "3.530000"
    monkeypatch.setattr(
        BankCurrencyRateRefreshService,
        "refresh_user_selected_rates",
        lambda *_args, **_kwargs: [],
    )
    failed_refresh = client.post(
        "/api/v1/currency/rate-options/refresh",
        params={
            "currency": "EUR",
            "base_currency": "BYN",
            "bank_code": "technobank",
        },
    )
    assert failed_refresh.status_code == 502
    assert "Не удалось обновить курс" in failed_refresh.json()["detail"]


def test_recurring_plan_rejects_second_confirmation_on_same_day(client: TestClient):
    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "10.00",
            "scheduled_date": "2026-08-19",
            "recurrence_enabled": True,
            "recurrence_frequency": "monthly",
        },
    )
    assert created.status_code == 201, created.text
    plan_id = created.json()["id"]
    first = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert first.status_code == 200, first.text
    duplicate = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert duplicate.status_code == 400
    assert "already confirmed today" in duplicate.json()["detail"]
    assert client.get("/api/v1/operations", params={"page": 1, "page_size": 20}).json()["total"] == 1


def test_skipped_foreign_plan_history_keeps_original_and_resolved_base_amount(client: TestClient):
    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "229.00",
            "currency": "EUR",
            "scheduled_date": "2026-08-19",
            "fx_rate_source": "manual",
            "fx_manual_rate": "3.50",
            "fx_payment_mode": "direct_conversion",
        },
    )
    assert created.status_code == 201, created.text
    skipped = client.post(f"/api/v1/plans/{created.json()['id']}/skip")
    assert skipped.status_code == 200, skipped.text
    event = client.get("/api/v1/plans/history").json()["items"][0]
    assert event["event_type"] == "skipped"
    assert event["original_amount"] == "229.00"
    assert event["currency"] == "EUR"
    assert event["base_currency"] == "BYN"
    assert event["amount"] == "801.50"
    assert event["fx_rate"] == "3.500000"
    assert event["fx_payment_mode"] == "direct_conversion"
