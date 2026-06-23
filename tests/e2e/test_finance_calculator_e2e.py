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
expect = sync_api.expect


@pytest.fixture(scope="module")
def static_server_url() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

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
def page_with_calculator_mock():
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"filters": {"kind": "", "q": ""}},
            "ui": {"active_section": "dashboard", "timezone": "Europe/Minsk", "currency": "BYN", "currency_position": "suffix"},
        },
    }

    def json_response(route, payload: dict | list, status: int = 200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def handler(route, request):
        path = urlparse(request.url).path
        method = request.method.upper()
        if path == "/api/v1/auth/telegram" and method == "POST":
            return json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})
        if path == "/api/v1/auth/public-config" and method == "GET":
            return json_response(route, {"telegram_bot_username": "", "browser_login_available": False})
        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "Calc User", "username": "calc_user", "status": "approved", "is_admin": False})
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
            return json_response(route, [])
        if path == "/api/v1/dashboard/summary" and method == "GET":
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00", "cashflow_total": "0.00"})
        if path == "/api/v1/dashboard/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/dashboard/analytics" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/dashboard/analytics/highlights" and method == "GET":
            return json_response(route, {"category_breakdown": [], "top_operations": [], "top_positions": [], "price_increases": []})
        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/currency/overview" and method == "GET":
            return json_response(route, {"tracked_currencies": [], "positions": [], "recent_trades": [], "current_rates": [], "base_currency": "BYN"})
        if path == "/api/v1/plans" and method == "GET":
            return json_response(route, {"items": [], "total": 0})
        if path == "/api/v1/plans/history" and method == "GET":
            return json_response(route, {"items": [], "total": 0})
        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page(viewport={"width": 390, "height": 760})
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


def _restore_mock_telegram(page):
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


def _open_app(page, static_server_url: str):
    page.goto(f"{static_server_url}/static/index.html")
    _restore_mock_telegram(page)
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
def test_finance_calculator_drawer_calculates_discount_and_fits_mobile(static_server_url: str, page_with_calculator_mock):
    page = page_with_calculator_mock
    _open_app(page, static_server_url)

    page.click("#financeCalculatorToggle")
    page.wait_for_selector("#financeCalculatorDrawer:not(.hidden)")
    page.fill("#financeCalculatorInput-price", "100")
    page.fill("#financeCalculatorInput-discount", "15")

    expect(page.locator("#financeCalculatorResult")).to_contain_text("Итоговая цена")
    expect(page.locator("#financeCalculatorResult")).to_contain_text("85,00")
    expect(page.locator("#financeCalculatorResult")).to_contain_text("15,00")

    geometry = page.evaluate(
        """
        () => {
          const drawer = document.getElementById('financeCalculatorDrawer').getBoundingClientRect();
          return {
            top: drawer.top,
            bottom: drawer.bottom,
            width: drawer.width,
            height: drawer.height,
            viewportWidth: window.innerWidth,
            viewportHeight: window.innerHeight,
          };
        }
        """
    )
    assert geometry["width"] <= geometry["viewportWidth"]
    assert geometry["bottom"] <= geometry["viewportHeight"] + 1
    assert geometry["height"] <= geometry["viewportHeight"] * 0.9
