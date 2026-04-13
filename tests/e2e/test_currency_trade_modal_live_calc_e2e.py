from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

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


@pytest.mark.e2e
def test_currency_trade_modal_keeps_preview_and_live_recalculates(static_server_url: str):
    def json_response(route, payload: dict | list, status: int = 200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def handler(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        method = request.method.upper()
        query = parsed.query

        if path == "/api/v1/auth/public-config" and method == "GET":
            return json_response(route, {"telegram_bot_username": "FinanceWeaselBot", "browser_login_available": False})
        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "Currency User", "username": "currency_user", "status": "approved", "is_admin": False})
        if path == "/api/v1/preferences" and method == "GET":
            return json_response(route, {"preferences_version": 1, "data": {"ui": {"active_section": "dashboard", "timezone": "Europe/Minsk"}, "currency": {"tracked_currencies": ["USD", "EUR"]}}})
        if path == "/api/v1/preferences" and method == "PUT":
            return json_response(route, {"preferences_version": 1, "data": {"ui": {"active_section": "dashboard", "timezone": "Europe/Minsk"}, "currency": {"tracked_currencies": ["USD", "EUR"]}}})
        if path == "/api/v1/categories/groups" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/categories" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/dashboard/summary" and method == "GET":
            return json_response(route, {
                "income_total": "0.00",
                "expense_total": "0.00",
                "balance": "0.00",
                "currency_current_value": "0.00",
                "currency_book_value": "0.00",
                "currency_result_value": "0.00",
                "tracked_currency_positions": [],
                "tracked_currency_rates": [],
            })
        if path == "/api/v1/dashboard/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/dashboard/analytics" and method == "GET":
            return json_response(route, {"points": [], "summary": {}})
        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/operations/item-templates" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/currency/overview" and method == "GET":
            currency = "USD"
            if "currency=EUR" in query:
                currency = "EUR"
            return json_response(route, {
                "base_currency": "BYN",
                "tracked_currencies": ["USD", "EUR"],
                "positions": [],
                "current_rates": [
                    {"currency": currency, "rate": "2.9652", "rate_date": "2026-03-27", "source": "nb"}
                ],
                "recent_trades": [],
                "total_current_value": "0.00",
                "total_book_value": "0.00",
                "total_result_value": "0.00",
                "active_positions": 0,
                "buy_volume_base": "0.00",
                "buy_trades_count": 0,
                "buy_average_rate": "0.0000",
                "sell_volume_base": "0.00",
                "sell_trades_count": 0,
                "sell_average_rate": "0.0000",
            })
        if path == "/api/v1/auth/telegram" and method == "POST":
            return json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})
        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page()
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
            page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
            page.wait_for_selector("#appShell:not(.hidden)")
            page.click("#addOperationCta")
            page.wait_for_selector("#createModal:not(.hidden)")
            page.locator('#createEntryModeSwitch button[data-entry-mode="currency"]').click()
            page.wait_for_selector("#createPreviewHeadCurrency:not(.hidden)")

            preview_rows = page.locator("#createPreviewBody tr")
            expect_rows = preview_rows.count()
            assert expect_rows == 1

            page.locator('#createCurrencySideSwitch button[data-currency-side="sell"]').click()
            page.locator("#currencyQuoteTotal").fill("3")
            page.locator("#currencyUnitPrice").fill("2.9652")
            page.wait_for_timeout(200)

            quantity_value = page.locator("#currencyQuantity").input_value()
            assert quantity_value.startswith("1.01")
            assert page.locator("#currencyTradeHint").text_content().strip().startswith("Будет получено примерно 3,00\u00a0ƃ")
            assert preview_rows.count() == 1
            assert "Продажа" in page.locator("#createPreviewBody").text_content()
            assert "1.01 USD" in page.locator("#createPreviewBody").text_content()

            page.locator("#currencyQuantity").fill("50.25")
            page.wait_for_timeout(200)
            quote_value = page.locator("#currencyQuoteTotal").input_value()
            assert quote_value.startswith("149.00")
            assert preview_rows.count() == 1
            assert "50.25 USD" in page.locator("#createPreviewBody").text_content()

            page.click("#closeCreateModalBtn")
            page.wait_for_selector("#createModal", state="hidden")
            page.click("#addOperationCta")
            page.wait_for_selector("#createModal:not(.hidden)")
            page.locator('#createEntryModeSwitch button[data-entry-mode="currency"]').click()
            page.wait_for_selector("#createPreviewHeadCurrency:not(.hidden)")
            page.locator('#createCurrencySideSwitch button[data-currency-side="sell"]').click()

            page.locator("#currencyUnitPrice").fill("")
            page.locator("#currencyQuantity").fill("20")
            page.locator("#currencyQuoteTotal").fill("60")
            page.wait_for_timeout(200)

            rate_value = page.locator("#currencyUnitPrice").input_value()
            assert rate_value.startswith("3.0000")
            assert page.locator("#currencyTradeHint").text_content().strip().startswith("Будет получено примерно 60,00\u00a0ƃ")
        finally:
            browser.close()
