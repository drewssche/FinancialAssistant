from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sync_api = pytest.importorskip("playwright.sync_api", reason="playwright is not installed")


@pytest.fixture(scope="module")
def static_server_url() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=str(repo_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                break
        except Exception:
            time.sleep(0.1)
    else:
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError("Static server did not start in time")

    try:
        yield url
    finally:
        process.terminate()
        process.wait(timeout=5)


@pytest.fixture()
def page_with_money_flow_api_mock():
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"mode": "operations", "filters": {"kind": "", "q": "", "source": "all"}, "sort_preset": "date"},
            "ui": {"active_section": "dashboard", "timezone": "Europe/Minsk", "currency": "BYN", "currency_position": "suffix"},
            "currency": {"tracked_currencies": ["USD", "EUR"]},
        },
    }
    metrics = {"last_money_flow_source": "all"}
    operations = []
    money_flow_items = [
        {
            "id": "fx:7001",
            "source_kind": "fx",
            "source_id": 7001,
            "flow_direction": "outflow",
            "event_date": "2026-03-06",
            "amount": "31.00",
            "original_amount": "31.00",
            "currency": "BYN",
            "base_currency": "BYN",
            "fx_rate": "1.000000",
            "title": "Покупка USD",
            "subtitle": "За BYN · курс 3.000000",
            "note": "покупка usd",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "trade_side": "buy",
            "can_open_source": True,
            "open_section": "currency",
            "open_label": "Сделка",
        },
        {
            "id": "debt-repayment:9102",
            "source_kind": "debt",
            "source_id": 9001,
            "flow_direction": "inflow",
            "event_date": "2026-03-04",
            "amount": "30.00",
            "original_amount": "30.00",
            "currency": "BYN",
            "base_currency": "BYN",
            "fx_rate": "1.000000",
            "title": "Мне вернули долг",
            "subtitle": "Иван",
            "note": "частично",
            "counterparty_id": 1,
            "counterparty_name": "Иван",
            "can_open_source": True,
            "open_section": "debts",
            "open_label": "История долга",
        },
        {
            "id": "debt-issuance:9101",
            "source_kind": "debt",
            "source_id": 9001,
            "flow_direction": "outflow",
            "event_date": "2026-03-03",
            "amount": "100.00",
            "original_amount": "100.00",
            "currency": "BYN",
            "base_currency": "BYN",
            "fx_rate": "1.000000",
            "title": "Я дал в долг",
            "subtitle": "Иван",
            "note": "на ремонт",
            "counterparty_id": 1,
            "counterparty_name": "Иван",
            "can_open_source": True,
            "open_section": "debts",
            "open_label": "История долга",
        },
        {
            "id": "operation:1",
            "source_kind": "operation",
            "source_id": 1,
            "flow_direction": "inflow",
            "event_date": "2026-03-01",
            "amount": "70.00",
            "original_amount": "70.00",
            "currency": "BYN",
            "base_currency": "BYN",
            "fx_rate": "1.000000",
            "title": "Без категории",
            "subtitle": "Обычная операция",
            "note": "salary",
            "can_open_source": False,
        },
    ]
    debt_cards = [
        {
            "counterparty_id": 1,
            "counterparty": "Иван",
            "principal_total": "100.00",
            "repaid_total": "30.00",
            "outstanding_total": "70.00",
            "status": "active",
            "nearest_due_date": "2026-04-01",
            "debts": [
                {
                    "id": 9001,
                    "counterparty_id": 1,
                    "direction": "lend",
                    "principal": "100.00",
                    "repaid_total": "30.00",
                    "forgiven_total": "0.00",
                    "outstanding_total": "70.00",
                    "start_date": "2026-03-03",
                    "due_date": "2026-04-01",
                    "note": "на ремонт",
                    "created_at": "2026-03-03T10:00:00Z",
                    "issuances": [
                        {"id": 9101, "amount": "100.00", "current_base_amount": "100.00", "issuance_date": "2026-03-03", "note": "на ремонт"},
                    ],
                    "repayments": [
                        {"id": 9102, "amount": "30.00", "current_base_amount": "30.00", "repayment_date": "2026-03-04", "note": "частично"},
                    ],
                    "forgivenesses": [],
                }
            ],
        }
    ]
    currency_overview = {
        "base_currency": "BYN",
        "tracked_currencies": ["USD", "EUR"],
        "total_book_value": "0.00",
        "total_current_value": "0.00",
        "total_result_value": "0.00",
        "total_unrealized_result_value": "0.00",
        "total_realized_result_value": "0.00",
        "total_combined_result_value": "0.00",
        "buy_volume_base": "31.00",
        "sell_volume_base": "0.00",
        "buy_average_rate": "3.000000",
        "sell_average_rate": "0.000000",
        "buy_trades_count": 1,
        "sell_trades_count": 0,
        "active_positions": 1,
        "positions": [],
        "recent_trades": [
            {
                "id": 7001,
                "side": "buy",
                "asset_currency": "USD",
                "quote_currency": "BYN",
                "quantity": "10.00",
                "unit_price": "3.000000",
                "fee": "1.00",
                "trade_date": "2026-03-06",
                "note": "покупка usd",
            }
        ],
        "current_rates": [{"currency": "USD", "rate": "3.1000", "rate_date": "2026-03-27", "source": "nb"}],
    }

    def json_response(route, payload: dict | list, status: int = 200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def handler(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        query = parse_qs(parsed.query)
        method = request.method.upper()

        if path == "/api/v1/auth/telegram" and method == "POST":
            return json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})
        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "Money Flow User", "username": "money_flow_user", "status": "approved", "is_admin": False})
        if path == "/api/v1/preferences":
            if method == "GET":
                return json_response(route, preferences)
            if method == "PUT":
                payload = json.loads(request.post_data or "{}")
                preferences["preferences_version"] = payload.get("preferences_version", preferences["preferences_version"])
                preferences["data"] = payload.get("data", preferences["data"])
                return json_response(route, preferences)
        if path == "/api/v1/categories/groups" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/categories" and method == "GET":
            if "page" in query and "page_size" in query:
                return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
            return json_response(route, [])
        if path == "/api/v1/dashboard/summary" and method == "GET":
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00"})
        if path == "/api/v1/operations" and method == "GET":
            return json_response(route, {"items": operations, "total": len(operations), "page": 1, "page_size": 20})
        if path == "/api/v1/operations/summary" and method == "GET":
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00", "total": 0})
        if path == "/api/v1/operations/money-flow" and method == "GET":
            source = (query.get("source") or ["all"])[0]
            metrics["last_money_flow_source"] = source
            items = money_flow_items if source == "all" else [item for item in money_flow_items if item["source_kind"] == source]
            return json_response(route, {"items": items, "total": len(items), "page": 1, "page_size": 20})
        if path == "/api/v1/operations/money-flow/summary" and method == "GET":
            source = (query.get("source") or ["all"])[0]
            items = money_flow_items if source == "all" else [item for item in money_flow_items if item["source_kind"] == source]
            income_total = sum(float(item["amount"]) for item in items if item["flow_direction"] == "inflow")
            expense_total = sum(float(item["amount"]) for item in items if item["flow_direction"] == "outflow")
            return json_response(route, {
                "income_total": f"{income_total:.2f}",
                "expense_total": f"{expense_total:.2f}",
                "balance": f"{income_total - expense_total:.2f}",
                "total": len(items),
            })
        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, debt_cards)
        if path == "/api/v1/currency/overview" and method == "GET":
            return json_response(route, currency_overview)
        if path == "/api/v1/currency/performance/history" and method == "GET":
            return json_response(route, {
                "base_currency": "BYN",
                "currency": "USD",
                "date_from": "2026-03-01",
                "date_to": "2026-03-31",
                "points": [
                    {
                        "point_date": "2026-03-06",
                        "book_value": "31.00",
                        "current_value": "31.00",
                        "unrealized_result_value": "0.00",
                        "realized_result_value": "0.00",
                        "total_result_value": "0.00",
                    }
                ],
            })
        if path == "/api/v1/test/money-flow-metrics" and method == "GET":
            return json_response(route, metrics)
        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page()
        page.add_init_script(
            """
            window.Telegram = {
              WebApp: {
                initData: "mock-init-data",
                ready() {},
                expand() {},
              }
            };
            """
        )
        page.route("**/api/v1/**", handler)
        try:
            yield page
        finally:
            browser.close()


def _open_app(page, static_server_url: str):
    page.goto(f"{static_server_url}/static/index.html")
    page.evaluate(
        """
        () => {
          window.Telegram = {
            WebApp: {
              initData: "mock-init-data",
              ready() {},
              expand() {},
            }
          };
        }
        """
    )
    page.evaluate("() => window.App.getRuntimeModule('session')?.refreshTelegramLoginUi?.()")
    if page.locator("#loginScreen:not(.hidden)").count():
        page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")


@pytest.mark.e2e
def test_operations_money_flow_mode_supports_source_filter_and_drilldown(static_server_url: str, page_with_money_flow_api_mock):
    page = page_with_money_flow_api_mock
    _open_app(page, static_server_url)

    page.click("button[data-section='operations']")
    page.wait_for_selector("#operationsSection:not(.hidden)")
    page.click("#operationsModeTabs button[data-operations-mode='money_flow']")
    page.wait_for_function(
        """
        () => document.querySelector('#operationsModeTabs .segmented-btn.active')?.dataset.operationsMode === 'money_flow'
        """
    )
    page.wait_for_selector("#operationsBody tr")

    table_text = page.locator("#operationsBody").inner_text()
    assert "Я дал в долг" in table_text
    assert "Мне вернули долг" in table_text
    assert "FX" in table_text
    assert "DEBT" in table_text

    page.click("#operationsSourceTabs button[data-operations-source='debt']")
    page.wait_for_function(
        """
        () => document.querySelector('#operationsSourceTabs .segmented-btn.active')?.dataset.operationsSource === 'debt'
        """
    )
    page.wait_for_function(
        """
        async () => {
          const response = await fetch('/api/v1/test/money-flow-metrics');
          const payload = await response.json();
          return payload.last_money_flow_source === 'debt';
        }
        """
    )
    debt_only_text = page.locator("#operationsBody").inner_text()
    assert "Я дал в долг" in debt_only_text
    assert "Покупка USD" not in debt_only_text

    page.evaluate(
        """
        () => window.App.actions.openMoneyFlowSource({
          sourceKind: 'debt',
          sourceId: '9001',
        })
        """
    )
    page.wait_for_selector("#debtHistoryModal:not(.hidden)")
    assert "Иван" in page.locator("#debtHistoryModal").inner_text()

    page.evaluate(
        """
        () => window.App.actions.openMoneyFlowSource({
          sourceKind: 'fx',
          sourceId: '7001',
        })
        """
    )
    page.wait_for_selector("#currencySection:not(.hidden)")
    page.wait_for_selector("#createModal:not(.hidden)")
    assert page.locator("#createTitle").inner_text().strip() == "Редактировать валютную сделку"
    assert page.locator("#currencyAsset").input_value() == "USD"
