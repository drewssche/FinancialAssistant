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
def page_with_currency_modal_api_mock():
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"filters": {"kind": "", "q": ""}},
            "ui": {"active_section": "dashboard", "timezone": "Europe/Minsk", "currency": "BYN", "currency_position": "suffix"},
            "currency": {"tracked_currencies": ["USD", "EUR"]},
        },
    }

    category_groups = [
        {
            "id": 201,
            "name": "Базовые траты",
            "kind": "expense",
            "accent_color": "#ff8a3d",
        },
    ]

    categories = [
        {
            "id": 101,
            "name": "Еда",
            "icon": "🍔",
            "kind": "expense",
            "group_id": 201,
            "group_name": "Базовые траты",
            "group_icon": None,
            "group_accent_color": "#ff8a3d",
            "is_system": False,
        },
    ]

    currency_overview = {
        "base_currency": "BYN",
        "tracked_currencies": ["USD", "EUR"],
        "total_book_value": "0.00",
        "total_current_value": "0.00",
        "total_result_value": "0.00",
        "buy_volume_base": "0.00",
        "sell_volume_base": "0.00",
        "buy_average_rate": "0.000000",
        "sell_average_rate": "0.000000",
        "buy_trades_count": 0,
        "sell_trades_count": 0,
        "active_positions": 0,
        "positions": [],
        "recent_trades": [],
        "current_rates": [
            {
                "currency": "USD",
                "rate": "2.9652",
                "rate_date": "2026-03-27",
                "source": "nb",
                "change_value": "-0.0012",
                "change_pct": "-0.04",
            },
            {
                "currency": "EUR",
                "rate": "3.4266",
                "rate_date": "2026-03-27",
                "source": "nb",
                "change_value": "0.0000",
                "change_pct": "0.00",
            },
        ],
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
            return json_response(route, category_groups)

        if path == "/api/v1/categories" and method == "GET":
            if "page" in query and "page_size" in query:
                return json_response(route, {"items": categories, "total": len(categories), "page": 1, "page_size": 20})
            return json_response(route, categories)

        if path == "/api/v1/dashboard/summary" and method == "GET":
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00"})

        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, [])

        if path == "/api/v1/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})

        if path == "/api/v1/currency/overview" and method == "GET":
            selected_currency = (query.get("currency") or [""])[0]
            if selected_currency:
                payload = dict(currency_overview)
                payload["current_rates"] = [item for item in currency_overview["current_rates"] if item["currency"] == selected_currency]
                payload["tracked_currencies"] = [selected_currency]
                return json_response(route, payload)
            return json_response(route, currency_overview)

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


def _login_via_mock_telegram(page):
    page.evaluate("() => window.App.getRuntimeModule('session')?.refreshTelegramLoginUi?.()")
    try:
        page.locator("#telegramLoginBtn").wait_for(state="visible", timeout=1200)
        page.click("#telegramLoginBtn")
        page.wait_for_selector("#appShell:not(.hidden)")
    except Exception:
        page.evaluate(
            """
            () => window.App.getRuntimeModule('session')?.tryAutoTelegramLogin?.().catch(() => null)
            """
        )
        page.wait_for_selector("#appShell:not(.hidden)")


@pytest.mark.e2e
def test_currency_trade_modal_keeps_preview_and_recalculates_both_fields(static_server_url: str, page_with_currency_modal_api_mock):
    page = page_with_currency_modal_api_mock
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
    _login_via_mock_telegram(page)

    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.click("#createEntryModeSwitch button[data-entry-mode='currency']")
    page.click("#createCurrencySideSwitch button[data-currency-side='sell']")

    page.fill("#currencyUnitPrice", "2.9652")
    page.fill("#currencyQuoteTotal", "3")

    page.wait_for_function(
        """
        () => {
          const quantity = document.querySelector('#currencyQuantity');
          const previewBody = document.querySelector('#createPreviewBody');
          return Boolean(quantity && previewBody && quantity.value && previewBody.children.length === 1);
        }
        """
    )

    quantity_value = page.locator("#currencyQuantity").input_value()
    assert quantity_value.startswith("1.01")
    assert page.locator("#createPreviewBody tr").count() == 1
    assert "1.01 USD" in page.locator("#createPreviewBody").inner_text()
    assert "2.9652" in page.locator("#createPreviewBody").inner_text()

    page.fill("#currencyQuantity", "2")
    page.wait_for_function(
        """
        () => {
          const quote = document.querySelector('#currencyQuoteTotal');
          return Boolean(quote && quote.value && quote.value.startsWith('5.93'));
        }
        """
    )

    assert page.locator("#currencyQuoteTotal").input_value().startswith("5.93")
    assert page.locator("#createPreviewBody tr").count() == 1
    preview_text = page.locator("#createPreviewBody").inner_text()
    assert "2.00 USD" in preview_text
    assert "5,93 руб." in preview_text


@pytest.mark.e2e
def test_currency_trade_modal_derives_rate_from_quantity_and_quote_total(static_server_url: str, page_with_currency_modal_api_mock):
    page = page_with_currency_modal_api_mock
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
    _login_via_mock_telegram(page)

    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.click("#createEntryModeSwitch button[data-entry-mode='currency']")

    page.fill("#currencyQuantity", "2")
    page.fill("#currencyQuoteTotal", "5.93")

    page.wait_for_function(
        """
        () => {
          const rate = document.querySelector('#currencyUnitPrice');
          const previewBody = document.querySelector('#createPreviewBody');
          return Boolean(rate && previewBody && rate.value && rate.value.startsWith('2.965') && previewBody.children.length === 1);
        }
        """
    )

    assert page.locator("#currencyUnitPrice").input_value().startswith("2.965")
    preview_text = page.locator("#createPreviewBody").inner_text()
    assert "2.00 USD" in preview_text
    assert "5,93 руб." in preview_text
    assert "2.965" in preview_text
