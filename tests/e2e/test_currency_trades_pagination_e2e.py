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


def _build_trade(index: int, currency: str) -> dict:
    day = (index % 28) + 1
    return {
        "id": index,
        "side": "buy" if index % 2 else "sell",
        "asset_currency": currency,
        "quote_currency": "BYN",
        "quantity": f"{100 + index:.6f}",
        "unit_price": "3.100000",
        "fee": "0.00",
        "trade_kind": "manual",
        "linked_operation_id": None,
        "trade_date": f"2026-03-{day:02d}",
        "note": f"{currency.lower()}-trade-{index}",
        "created_at": "2026-03-27T10:00:00Z",
    }


@pytest.fixture()
def page_with_currency_pagination_api_mock():
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"filters": {"kind": "", "q": ""}},
            "analytics": {"tab": "calendar"},
            "ui": {
                "active_section": "dashboard",
                "timezone": "Europe/Minsk",
                "currency": "BYN",
                "currency_position": "suffix",
            },
            "currency": {"tracked_currencies": ["USD", "EUR"]},
        },
    }

    usd_trades = [_build_trade(index, "USD") for index in range(1, 26)]
    eur_trades = [_build_trade(100 + index, "EUR") for index in range(1, 8)]
    all_trades = list(reversed(eur_trades + usd_trades))
    trades_calls: list[dict[str, int | str]] = []

    def json_response(route, payload: dict | list, status: int = 200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def resolve_trade_items(currency: str | None) -> list[dict]:
        if currency == "USD":
            return list(reversed(usd_trades))
        if currency == "EUR":
            return list(reversed(eur_trades))
        return all_trades

    def handler(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        query = parse_qs(parsed.query)
        method = request.method.upper()

        if path == "/api/v1/auth/public-config" and method == "GET":
            return json_response(route, {"telegram_bot_username": "FinanceWeaselBot", "browser_login_available": True})

        if path == "/api/v1/auth/telegram" and method == "POST":
            return json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})

        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "E2E User", "username": "e2e_user", "status": "approved", "is_admin": False})

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
            return json_response(
                route,
                {
                    "income_total": "0.00",
                    "expense_total": "0.00",
                    "balance": "0.00",
                    "currency_current_value": "0.00",
                    "currency_book_value": "0.00",
                    "currency_result_value": "0.00",
                    "tracked_currency_positions": [],
                    "tracked_currency_rates": [],
                    "active_debt_cards": 0,
                    "debt_lend_outstanding": "0.00",
                    "debt_borrow_outstanding": "0.00",
                    "debt_net_position": "0.00",
                },
            )

        if path == "/api/v1/dashboard/plans" and method == "GET":
            return json_response(route, {"items": [], "kpi": {"total": 0}})

        if path == "/api/v1/dashboard/debts/preview" and method == "GET":
            return json_response(route, [])

        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, [])

        if path == "/api/v1/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})

        if path == "/api/v1/dashboard/analytics" and method == "GET":
            return json_response(route, {"points": [], "summary": {}})

        if path == "/api/v1/currency/overview" and method == "GET":
            selected_currency = ((query.get("currency") or [""])[0] or "").upper() or None
            tracked = [selected_currency] if selected_currency else ["USD", "EUR"]
            current_rates = [
                {
                    "currency": "USD",
                    "rate": "3.200000",
                    "rate_date": "2026-03-27",
                    "source": "manual",
                    "previous_rate": "3.180000",
                    "change_value": "0.020000",
                    "change_pct": 0.6289,
                },
                {
                    "currency": "EUR",
                    "rate": "3.450000",
                    "rate_date": "2026-03-27",
                    "source": "manual",
                    "previous_rate": "3.440000",
                    "change_value": "0.010000",
                    "change_pct": 0.2907,
                },
            ]
            if selected_currency:
                current_rates = [item for item in current_rates if item["currency"] == selected_currency]
            return json_response(
                route,
                {
                    "base_currency": "BYN",
                    "tracked_currencies": tracked,
                    "total_book_value": "0.00",
                    "total_current_value": "0.00",
                    "total_result_value": "0.00",
                    "total_unrealized_result_value": "0.00",
                    "total_realized_result_value": "0.00",
                    "total_combined_result_value": "0.00",
                    "buy_volume_base": "0.00",
                    "sell_volume_base": "0.00",
                    "buy_average_rate": "0.000000",
                    "sell_average_rate": "0.000000",
                    "buy_trades_count": 0,
                    "sell_trades_count": 0,
                    "active_positions": 0,
                    "positions": [],
                    "recent_trades": [],
                    "current_rates": current_rates,
                },
            )

        if path == "/api/v1/currency/trades" and method == "GET":
            selected_currency = ((query.get("currency") or [""])[0] or "").upper() or None
            page = max(1, int((query.get("page") or ["1"])[0]))
            page_size = max(1, int((query.get("page_size") or ["20"])[0]))
            items = resolve_trade_items(selected_currency)
            start = (page - 1) * page_size
            stop = start + page_size
            trades_calls.append({"currency": selected_currency or "all", "page": page, "page_size": page_size})
            return json_response(
                route,
                {
                    "items": items[start:stop],
                    "total": len(items),
                    "page": page,
                    "page_size": page_size,
                },
            )

        if path == "/api/v1/currency/performance/history" and method == "GET":
            return json_response(
                route,
                {
                    "base_currency": "BYN",
                    "currency": ((query.get("currency") or ["USD"])[0] or "USD").upper(),
                    "date_from": "2026-01-01",
                    "date_to": "2026-03-27",
                    "points": [
                        {
                            "point_date": "2026-03-26",
                            "book_value": "0.00",
                            "current_value": "0.00",
                            "unrealized_result_value": "0.00",
                            "realized_result_value": "0.00",
                            "total_result_value": "0.00",
                        },
                        {
                            "point_date": "2026-03-27",
                            "book_value": "0.00",
                            "current_value": "0.00",
                            "unrealized_result_value": "0.00",
                            "realized_result_value": "0.00",
                            "total_result_value": "0.00",
                        },
                    ],
                },
            )

        if path == "/api/v1/currency/rates/history" and method == "GET":
            selected_currency = ((query.get("currency") or ["USD"])[0] or "USD").upper()
            base_rate = "3.200000" if selected_currency == "USD" else "3.450000"
            return json_response(
                route,
                [
                    {"currency": selected_currency, "rate": base_rate, "rate_date": "2026-03-26", "source": "manual"},
                    {"currency": selected_currency, "rate": base_rate, "rate_date": "2026-03-27", "source": "manual"},
                ],
            )

        if path == "/api/v1/currency/rates/history/fill" and method == "POST":
            selected_currency = ((query.get("currency") or ["USD"])[0] or "USD").upper()
            return json_response(route, [{"currency": selected_currency, "rate": "3.200000", "rate_date": "2026-03-27", "source": "manual"}])

        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")

        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page._currency_trades_calls = trades_calls
        page.add_init_script(
            """
            window.localStorage.setItem("access_token", "e2e-token");
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


@pytest.mark.e2e
def test_currency_section_infinite_scroll_loads_second_page(static_server_url: str, page_with_currency_pagination_api_mock):
    page = page_with_currency_pagination_api_mock
    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.wait_for_selector("#appShell:not(.hidden)")

    page.evaluate("() => window.App.actions.switchSection?.('currency')")
    page.wait_for_selector("#currencySection:not(.hidden)")
    page.click("button[data-currency-filter='USD']")
    page.wait_for_function("() => document.querySelectorAll('#currencyTradesBody tr').length === 20", timeout=5000)

    assert page.locator("#currencyTradesBody tr").count() == 20
    state = page.evaluate(
        """
        () => ({
          activeSection: window.App.state.activeSection,
          hasMore: window.App.state.currencyTradesHasMore,
          sentinelHidden: document.getElementById('currencyTradesInfiniteSentinel')?.classList.contains('hidden'),
        })
        """
    )
    assert state["activeSection"] == "currency"
    assert state["hasMore"] is True
    assert state["sentinelHidden"] is False
    page.evaluate("() => window.App.getRuntimeModule('currency')?.loadMoreCurrencyTrades?.()")
    page.wait_for_function("() => document.querySelectorAll('#currencyTradesBody tr').length === 25", timeout=5000)

    assert page.locator("#currencyTradesBody tr").count() == 25
    calls = getattr(page, "_currency_trades_calls", [])
    assert {"currency": "USD", "page": 1, "page_size": 20} in calls
    assert {"currency": "USD", "page": 2, "page_size": 20} in calls


@pytest.mark.e2e
def test_analytics_currency_section_infinite_scroll_loads_second_page(static_server_url: str, page_with_currency_pagination_api_mock):
    page = page_with_currency_pagination_api_mock
    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.wait_for_selector("#appShell:not(.hidden)")

    page.evaluate("() => window.App.actions.switchSection?.('analytics')")
    page.wait_for_selector("#analyticsSection:not(.hidden)")
    page.click("button[data-analytics-tab='currency']")
    page.wait_for_selector("#analyticsCurrencyPanel:not(.hidden)")
    page.click("button[data-analytics-currency-filter='USD']")
    page.wait_for_function("() => document.querySelectorAll('#analyticsCurrencyTradesBody tr').length === 20", timeout=5000)

    assert page.locator("#analyticsCurrencyTradesBody tr").count() == 20
    state = page.evaluate(
        """
        () => ({
          activeSection: window.App.state.activeSection,
          analyticsTab: window.App.state.analyticsTab,
          hasMore: window.App.state.analyticsCurrencyTradesHasMore,
          sentinelHidden: document.getElementById('analyticsCurrencyTradesInfiniteSentinel')?.classList.contains('hidden'),
        })
        """
    )
    assert state["activeSection"] == "analytics"
    assert state["analyticsTab"] == "currency"
    assert state["hasMore"] is True
    assert state["sentinelHidden"] is False
    page.evaluate("() => window.App.getRuntimeModule('analytics-currency-module')?.loadMoreAnalyticsCurrencyTrades?.()")
    page.wait_for_function("() => document.querySelectorAll('#analyticsCurrencyTradesBody tr').length === 25", timeout=5000)

    assert page.locator("#analyticsCurrencyTradesBody tr").count() == 25
    calls = getattr(page, "_currency_trades_calls", [])
    assert {"currency": "USD", "page": 1, "page_size": 20} in calls
    assert {"currency": "USD", "page": 2, "page_size": 20} in calls
