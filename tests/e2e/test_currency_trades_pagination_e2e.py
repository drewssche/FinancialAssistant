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

from tests.api import test_currency_api
from tests.e2e.test_analytics_mobile_e2e import _open_context_report

currency_api = test_currency_api.client
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
            "currency": {"tracked_currencies": ["USD", "EUR", "RUB"], "bank_rate_banks": ["priorbank", "bsb"]},
        },
    }

    usd_trades = [_build_trade(index, "USD") for index in range(1, 26)]
    eur_trades = [_build_trade(100 + index, "EUR") for index in range(1, 8)]
    all_trades = list(reversed(eur_trades + usd_trades))
    trades_calls: list[dict[str, int | str]] = []
    digest_calls: list[dict[str, str]] = []

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

        if path == "/api/v1/currency/rate-options":
            currency = query["currency"][0]
            return json_response(route, {
                "currency": currency, "base_currency": "BYN", "display_scale": 100 if currency == "RUB" else 1,
                "nbrb_rate": None, "providers": [
                    {"bank_code": "priorbank", "bank_name": "Приорбанк", "channel_label": "онлайн"},
                    {"bank_code": "bsb", "bank_name": "БСБ Банк", "channel_label": "наличные"},
                ],
                "bank_rates": [{"bank_code": "priorbank", "sell_unit_rate": "0.038", "buy_unit_rate": "0.034",
                                "fetched_at": "2026-03-01T15:00:00Z", "stale": True}],
            })
        if path == "/api/v1/currency/rates/refresh" and method == "POST":
            return json_response(route, [])

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
            items = [item for item in resolve_trade_items(selected_currency)
                     if query.get("date_from", [""])[0] <= item["trade_date"] <= query.get("date_to", ["9999"])[0]]
            sort_by = (query.get("sort_by") or ["trade_date"])[0]
            if sort_by != "trade_date":
                numeric = sort_by in {"quantity", "unit_price"}
                items = sorted(items, key=lambda item: float(item[sort_by]) if numeric else item.get(sort_by, ""),
                               reverse=(query.get("sort_dir") or ["desc"])[0] == "desc")
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

        if path == "/api/v1/currency/telegram-digest/send" and method == "POST":
            digest_calls.append({"method": method, "path": path})
            time.sleep(0.35)
            return json_response(
                route,
                {
                    "delivery_format": "photo",
                    "sent_at": "2026-08-26T13:00:00+03:00",
                    "scheduled_slot_consumed": False,
                    "tracked_currencies": ["USD", "EUR"],
                    "audit_recorded": True,
                    "message": "Ручной валютный дайджест доставлен из тестового ответа",
                },
            )

        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")

        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page._currency_trades_calls = trades_calls
        page._currency_digest_calls = digest_calls
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
@pytest.mark.parametrize("width", [1280, 430])
def test_currency_trade_kebab_edit_and_delete_close_menu(static_server_url, page_with_currency_pagination_api_mock, width):
    page = page_with_currency_pagination_api_mock
    page.set_viewport_size({"width": width, "height": 950})
    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.evaluate("window.App.actions.switchSection('currency')")
    page.locator("[data-currency-view='portfolio']").click()
    trigger = page.locator('#currencyTradesBody [data-table-menu-trigger="currency-trade-25"]')
    menu = page.locator('[data-table-menu="currency-trade-25"]')
    trigger.click()
    assert menu.evaluate("node => node.parentElement === document.body")
    menu.locator("[data-edit-currency-trade-id]").click()
    sync_api.expect(page.locator("#createModal")).to_be_visible()
    sync_api.expect(page.locator("#currencyAsset")).to_have_value("USD")
    assert float(page.locator("#currencyQuantity").input_value().replace(",", ".")) == 125
    sync_api.expect(menu).to_be_hidden()
    page.locator("#closeCreateModalBtn").click()
    trigger.click()
    menu.locator("[data-delete-currency-trade-id]").click()
    sync_api.expect(page.locator("#confirmModal")).to_be_visible()
    sync_api.expect(menu).to_be_hidden()
    page.locator("#confirmCancelBtn").click()
    sync_api.expect(page.locator('#currencyTradesBody [data-currency-trade-row-id="25"]')).to_be_visible()


@pytest.mark.e2e
def test_currency_column_sort_survives_pagination(static_server_url, page_with_currency_pagination_api_mock):
    page = page_with_currency_pagination_api_mock
    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.evaluate("window.App.actions.switchSection('currency')")
    page.locator("[data-currency-view='portfolio']").click()
    page.click("[data-currency-filter='USD']")
    page.wait_for_function("document.querySelectorAll('#currencyTradesBody tr').length === 20")
    table = page.locator("#currencyTradesBody").locator("xpath=ancestor::table")
    quantity = table.locator('th[data-sort-key="quantity"]')
    quantity.locator("button").click()
    sync_api.expect(quantity).to_have_attribute("aria-sort", "ascending")
    sync_api.expect(page.locator("#currencyTradesBody tr").first).to_contain_text("101")
    page.evaluate("window.App.getRuntimeModule('currency').loadMoreCurrencyTrades()")
    page.wait_for_function("document.querySelectorAll('#currencyTradesBody tr').length === 25")
    sync_api.expect(page.locator("#currencyTradesBody tr").last).to_contain_text("125")
    quantity.locator("button").click()
    sync_api.expect(page.locator("#currencyTradesBody tr").first).to_contain_text("125")
    sync_api.expect(quantity).to_have_attribute("aria-sort", "descending")
    assert page.locator("#currencyTradesBody tr").count() == 20


@pytest.mark.e2e
def test_currency_section_infinite_scroll_loads_second_page(static_server_url: str, page_with_currency_pagination_api_mock):
    page = page_with_currency_pagination_api_mock
    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.wait_for_selector("#appShell:not(.hidden)")

    page.evaluate("() => window.App.actions.switchSection?.('currency')")
    page.wait_for_selector("#currencySection:not(.hidden)")
    page.locator("[data-currency-view='portfolio']").click()
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
def test_currency_sort_ignores_out_of_order_response(static_server_url, page_with_currency_pagination_api_mock):
    page = page_with_currency_pagination_api_mock
    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.evaluate("window.App.actions.switchSection('currency')")
    page.locator("[data-currency-view='portfolio']").click()
    page.click("button[data-currency-filter='USD']")
    page.wait_for_function("!window.App.state.currencyTradesLoading")
    pending = []
    page.route("**/api/v1/currency/trades?**", lambda route: pending.append(route))
    header = page.locator('#currencyTradesBody').locator('xpath=ancestor::table').locator('th[data-sort-key="quantity"]')
    header.locator("button").click()
    page.wait_for_timeout(100)
    header.locator("button").click()
    page.wait_for_timeout(100)
    assert len(pending) == 2
    for route, ident in [(pending[1], 25), (pending[0], 1)]:
        route.fulfill(status=200, content_type="application/json", body=json.dumps({
            "items": [_build_trade(ident, "USD")], "total": 1, "page": 1, "page_size": 20,
        }))
        page.wait_for_timeout(100)
    sync_api.expect(header).to_have_attribute("aria-sort", "descending")
    sync_api.expect(page.locator('#currencyTradesBody tr').first).to_contain_text("125")
    assert page.evaluate("window.App.state.currencyTradesItems[0].id") == 25


@pytest.mark.e2e
@pytest.mark.parametrize("width", [320, 390, 1440])
def test_quotes_and_exchange_journal_are_independent(static_server_url, page_with_currency_pagination_api_mock, width):
    page = page_with_currency_pagination_api_mock
    page.set_viewport_size({"width": width, "height": 900})
    calls = []
    page.on("request", lambda req: calls.append((req.method, req.url)))
    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.wait_for_selector("#appShell:not(.hidden)")
    calls.clear()
    page.evaluate("window.App.actions.switchSection('currency')")
    sync_api.expect(page.locator("#currencyQuotesList")).to_contain_text("НБРБ")
    page.locator("[data-quote-currency=RUB]").click()
    row = page.locator(".fx-quotes tbody tr").first
    sync_api.expect(row.locator("td").nth(0)).to_have_text("3.8000")
    sync_api.expect(row.locator("td").nth(1)).to_have_text("3.4000")
    sync_api.expect(row).to_contain_text("Курс устарел")
    sync_api.expect(page.locator(".fx-quotes caption")).to_have_text("BYN за 100 RUB")
    sync_api.expect(page.locator(".fx-quotes tbody tr").nth(1)).to_contain_text("Нет котировки")
    assert not any("/currency/trades?" in url or "/history?" in url for _, url in calls)
    assert page.locator("#currencySection").evaluate("node => node.getBoundingClientRect().right <= innerWidth + 1")
    page.locator("#currencyRefreshQuotesBtn").click()
    page.wait_for_function("!document.querySelector('#currencyRefreshQuotesBtn').disabled")
    assert any(method == "POST" and "/rates/refresh?currency=RUB" in url for method, url in calls)
    page.locator("#openCurrencyRatePanelBtn").click()
    sync_api.expect(page.locator("#currencyRatePanel")).to_be_visible()
    page.locator("#closeCurrencyRatePanelBtn").click()
    page.locator("[data-currency-view=portfolio]").click()
    sync_api.expect(page.locator("#currencyTradesBody")).to_contain_text("Купил")
    page.locator("#currencyTradesPeriod").select_option("7")
    sync_api.expect(page.locator("#currencyTradesBody")).to_contain_text("За выбранный период обменов нет")
    assert any("date_from=" in url and "date_to=" in url for _, url in calls)
    assert not any("/performance/history" in url for _, url in calls)
    page.locator("#currencyResultDetails summary").click()
    page.wait_for_function("document.querySelector('#currencyExchangeResult').textContent.includes('обменов')")
    assert any("/performance/history" in url for _, url in calls)
    page.locator("#currencyTradesPeriod").select_option("all_time")
    sync_api.expect(page.locator("#currencyTradesBody")).to_contain_text("Купил")
    sync_api.expect(page.get_by_role("button", name="Записать обмен")).to_have_count(1)


@pytest.mark.e2e
def test_manual_currency_digest_send_is_shared_across_currency_views(
    static_server_url: str,
    page_with_currency_pagination_api_mock,
):
    page = page_with_currency_pagination_api_mock
    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.wait_for_selector("#dashboardSection:not(.hidden)")

    currency_button = page.locator("#currencySendDigestBtn")
    analytics_button = page.locator("#analyticsSendCurrencyDigestBtn")
    expect = sync_api.expect

    expect(page.locator("#dashboardSendCurrencyDigestBtn")).to_have_count(0)
    page.evaluate("() => window.App.actions.switchSection('currency')")
    page.locator("[data-currency-view='portfolio']").click()
    expect(currency_button).to_be_visible()
    expect(currency_button).to_have_count(1)
    expect(analytics_button).to_have_count(1)

    pending_states = page.evaluate(
        """
        () => {
          const ids = [
            "currencySendDigestBtn",
            "analyticsSendCurrencyDigestBtn",
          ];
          document.getElementById(ids[0]).click();
          window.App.getRuntimeModule("currency-digest-actions").sendCurrencyDigest();
          return ids.map((id) => {
            const button = document.getElementById(id);
            return {
              id,
              disabled: button.disabled,
              ariaBusy: button.getAttribute("aria-busy"),
              text: button.getAttribute("aria-label"),
            };
          });
        }
        """
    )

    assert pending_states == [
        {
            "id": "currencySendDigestBtn",
            "disabled": True,
            "ariaBusy": "true",
            "text": "Отправляем дайджест",
        },
        {
            "id": "analyticsSendCurrencyDigestBtn",
            "disabled": True,
            "ariaBusy": "true",
            "text": "Отправляем дайджест",
        },
    ]

    expect(page.locator("#toastArea")).to_contain_text(
        "Ручной валютный дайджест доставлен из тестового ответа",
        timeout=5_000,
    )
    calls = getattr(page, "_currency_digest_calls", [])
    assert calls == [{"method": "POST", "path": "/api/v1/currency/telegram-digest/send"}]

    for button in (currency_button, analytics_button):
        expect(button).to_be_enabled()
        assert button.get_attribute("aria-busy") is None
        expect(button).to_have_attribute("aria-label", "Отправить дайджест")

    page.evaluate("() => window.App.actions.switchSection?.('analytics')")
    page.wait_for_selector("#analyticsSection:not(.hidden)")
    _open_context_report(page, "currency")
    page.wait_for_selector("#analyticsCurrencyPanel:not(.hidden)")
    expect(analytics_button).to_be_visible()


@pytest.mark.e2e
def test_exchange_at_historical_rate_and_manual_amounts(static_server_url, page_with_currency_pagination_api_mock, currency_api):
    page = page_with_currency_pagination_api_mock
    page.set_viewport_size({"width": 390, "height": 900})
    for date, rate in [("2026-01-09", "3.1"), ("2026-01-12", "3.4"), ("2026-11-19", "4")]:
        response = currency_api.put("/api/v1/currency/rates/current", json={"currency": "USD", "rate": rate, "rate_date": date})
        assert response.is_success, response.text
    old = currency_api.post("/api/v1/currency/trades", json={
        "asset_currency": "CHF", "side": "buy", "quantity": "12.345678", "unit_price": "3.123456",
        "fee": "0.75", "trade_date": "2025-12-20", "note": "Архив",
    })
    assert old.is_success, old.text

    def exchange_api(route):
        request = route.request
        path = urlparse(request.url).path
        assert path in {"/api/v1/currency/rates/history", "/api/v1/currency/rate-options", "/api/v1/currency/overview",
                        "/api/v1/currency/trades", f"/api/v1/currency/trades/{old.json()['id']}"}
        response = currency_api.request(request.method, path, params=parse_qs(urlparse(request.url).query),
                                        json=request.post_data_json if request.post_data else None)
        route.fulfill(status=response.status_code, content_type="application/json", body=response.content)

    page.route("**/api/v1/currency/**", exchange_api)
    page.clock.set_fixed_time("2026-11-18T21:15:00Z")
    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.evaluate("window.App.actions.switchSection('currency')")
    page.get_by_role("button", name="Записать обмен").click()
    date = page.locator("#currencyTradeDateModal")
    rate = page.locator("#currencyUnitPrice")
    prior = page.locator("#currencyUsePriorRate")
    qty = page.locator("#currencyQuantity")
    total = page.locator("#currencyQuoteTotal")
    sync_api.expect(date).to_have_value("2026-11-19")
    date.fill("2026-01-12")
    sync_api.expect(rate).to_have_value("3.4000")
    sync_api.expect(page.locator("#currencyTradeRateOrigin")).to_contain_text("12.01.2026")
    qty.fill("10")
    sync_api.expect(total).to_have_value("34.00")
    date.fill("2026-01-10")
    sync_api.expect(prior).to_contain_text("09.01.2026")
    sync_api.expect(rate).to_have_value("")
    sync_api.expect(total).to_have_value("")
    prior.click()
    sync_api.expect(total).to_have_value("31.00")
    date.fill("2026-01-08")
    sync_api.expect(page.locator("#currencyTradeRateOrigin")).to_contain_text("На выбранную дату курса нет")
    sync_api.expect(prior).to_be_hidden()
    sync_api.expect(total).to_have_value("")
    total.fill("36")
    sync_api.expect(rate).to_have_value("3.6000")
    date.fill("2026-01-12")
    sync_api.expect(total).to_have_value("36")
    with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/currency/trades")) as saving:
        page.locator("#submitCreateOperationBtn").click()
    assert saving.value.status == 201
    sync_api.expect(page.locator("#createModal")).to_be_hidden()

    page.locator("[data-currency-view=portfolio]").click()
    sync_api.expect(page.locator("#currencyTradesBody")).to_contain_text("36 BYN")
    page.get_by_role("button", name="Записать обмен").click()
    page.locator("[data-currency-side=sell]").click()
    date.fill("2026-01-14")
    sync_api.expect(prior).to_be_visible()
    qty.fill("3")
    total.fill("12")
    with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/currency/trades")) as sale:
        page.locator("#submitCreateOperationBtn").click()
    assert sale.value.status == 201
    sync_api.expect(page.locator("#createModal")).to_be_hidden()
    sync_api.expect(page.locator("#currencyTradesBody")).to_contain_text("Продал 3 USD за 12 BYN")

    page.locator("[data-currency-filter=USD]").click()
    sync_api.expect(page.locator(f"[data-currency-trade-row-id='{old.json()['id']}']")).to_have_count(0)
    page.evaluate("id => window.App.getRuntimeModule('currency').openCurrencyTradeEdit(id)", old.json()["id"])
    sync_api.expect(page.locator("#currencyAsset")).to_have_value("CHF")
    sync_api.expect(rate).to_have_value("3.123456")
    page.locator("#currencyNote").fill("Архивная запись")
    with page.expect_response(lambda response: response.request.method == "PATCH") as edited:
        page.locator("#submitCreateOperationBtn").click()
    assert edited.value.status == 200
    records = currency_api.get("/api/v1/currency/trades").json()["items"]
    assert [(r["side"], r["asset_currency"], r["quantity"], r["unit_price"], r["fee"], r["trade_date"]) for r in records] == [
        ("sell", "USD", "3.000000", "4.000000", "0.00", "2026-01-14"),
        ("buy", "USD", "10.000000", "3.600000", "0.00", "2026-01-12"),
        ("buy", "CHF", "12.345678", "3.123456", "0.75", "2025-12-20"),
    ]


@pytest.mark.e2e
def test_delayed_rate_respects_new_date_and_entered_amounts(static_server_url, page_with_currency_pagination_api_mock):
    page = page_with_currency_pagination_api_mock
    pending = {}

    def reply(route, day, rate):
        route.fulfill(json=[{"currency": "USD", "source": "manual", "rate_date": day, "rate": rate}])

    def hold_historical_dates(route):
        day = parse_qs(urlparse(route.request.url).query)["date_to"][0]
        if day in {"2026-01-12", "2026-01-13"}:
            pending[day] = route
        else:
            reply(route, day, "4")

    page.route("**/currency/rates/history?**", hold_historical_dates)
    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.evaluate("window.App.actions.switchSection('currency')")
    page.get_by_role("button", name="Записать обмен").click()
    date = page.locator("#currencyTradeDateModal")
    rate = page.locator("#currencyUnitPrice")
    sync_api.expect(rate).to_have_value("4.0000")
    with page.expect_request(lambda req: "date_to=2026-01-12" in req.url):
        date.fill("2026-01-12")
    date.fill("2026-01-14")
    sync_api.expect(page.locator("#currencyTradeRateOrigin")).to_contain_text("14.01.2026")
    with page.expect_response(lambda res: "date_to=2026-01-12" in res.url):
        reply(pending["2026-01-12"], "2026-01-12", "2.7")
    sync_api.expect(rate).to_have_value("4.0000")
    sync_api.expect(page.locator("#currencyTradeRateOrigin")).to_contain_text("14.01.2026")
    with page.expect_request(lambda req: "date_to=2026-01-13" in req.url):
        date.fill("2026-01-13")
    page.locator("#currencyQuantity").fill("10")
    page.locator("#currencyQuoteTotal").fill("31")
    with page.expect_response(lambda res: "date_to=2026-01-13" in res.url):
        reply(pending["2026-01-13"], "2026-01-13", "2.8")
    sync_api.expect(rate).to_have_value("3.1000")
    sync_api.expect(page.locator("#currencyTradeRateOrigin")).to_contain_text("Рассчитан по введённым суммам")
