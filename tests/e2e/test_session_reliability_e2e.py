from __future__ import annotations

import base64
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


def _fake_token(expires_in_minutes: int) -> str:
    def encode(payload: dict) -> str:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    now = int(time.time())
    return f"{encode({'alg': 'HS256', 'typ': 'JWT'})}.{encode({'sub': '1', 'iat': now, 'exp': now + expires_in_minutes * 60})}.signature"


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
def session_page():
    counters = {"telegram_auth": 0, "refresh": 0, "protected": 0}
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
        if path == "/api/v1/auth/public-config":
            return json_response(route, {"telegram_bot_username": "", "browser_login_available": False})
        if path == "/api/v1/auth/telegram" and method == "POST":
            counters["telegram_auth"] += 1
            return json_response(route, {"access_token": _fake_token(20), "token_type": "bearer"})
        if path == "/api/v1/auth/refresh" and method == "POST":
            counters["refresh"] += 1
            return json_response(route, {"access_token": _fake_token(30), "token_type": "bearer"})
        if path == "/api/v1/session-test/protected":
            counters["protected"] += 1
            if counters["protected"] == 1:
                return json_response(route, {"detail": "Expired test token"}, status=401)
            return json_response(route, {"ok": True})
        if path == "/api/v1/users/me":
            return json_response(route, {"id": 1, "display_name": "Session User", "username": "session_user", "status": "approved", "is_admin": False})
        if path == "/api/v1/preferences":
            if method == "GET":
                return json_response(route, preferences)
            return json_response(route, preferences)
        if path == "/api/v1/categories/groups":
            return json_response(route, [])
        if path == "/api/v1/categories":
            return json_response(route, [])
        if path == "/api/v1/dashboard/summary":
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00", "cashflow_total": "0.00"})
        if path in {"/api/v1/dashboard/operations", "/api/v1/dashboard/analytics"}:
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/dashboard/analytics/highlights":
            return json_response(route, {"category_breakdown": [], "top_operations": [], "top_positions": [], "frequent_positions": [], "price_increases": []})
        if path == "/api/v1/debts/cards":
            return json_response(route, [])
        if path == "/api/v1/currency/overview":
            return json_response(route, {"tracked_currencies": [], "positions": [], "recent_trades": [], "current_rates": [], "base_currency": "BYN"})
        if path in {"/api/v1/plans", "/api/v1/plans/history"}:
            return json_response(route, {"items": [], "total": 0})
        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.route(
            "https://telegram.org/js/telegram-web-app.js",
            lambda route: route.fulfill(
                content_type="application/javascript",
                body="""
                  window.Telegram = { WebApp: {
                    initData: '', platform: 'web', version: '8.0',
                    ready() {}, expand() {}, setHeaderColor() {}, setBackgroundColor() {}, onEvent() {}
                  }};
                  setTimeout(() => { window.Telegram.WebApp.initData = 'delayed-init-data'; }, 350);
                """,
            ),
        )
        page.route("**/api/v1/**", handler)
        try:
            yield page, counters
        finally:
            browser.close()


@pytest.mark.e2e
def test_delayed_telegram_startup_and_session_refresh_preserve_operation_modal(static_server_url: str, session_page):
    page, counters = session_page

    page.goto(f"{static_server_url}/static/index.html")
    motion_name = page.locator("#loginLoading .login-brand-motion").evaluate("node => getComputedStyle(node).animationName")
    assert motion_name == "loginBrandFloat"
    page.wait_for_selector("#appShell:not(.hidden)")
    assert counters["telegram_auth"] == 1
    assert page.evaluate("() => performance.getEntriesByType('navigation')[0]?.type") == "navigate"

    expect(page.locator("#sessionRemainingLabel")).to_contain_text("Сессия")
    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.fill("#opAmount", "129.90")
    page.fill("#opNote", "Большой чек не должен закрыться")
    page.click("#createSessionRefreshBtn")
    page.wait_for_function("() => document.getElementById('sessionRemainingLabel')?.textContent.includes('30 мин')")

    assert counters["refresh"] == 1
    expect(page.locator("#createModal")).to_be_visible()
    expect(page.locator("#opAmount")).to_have_value("129.90")
    expect(page.locator("#opNote")).to_have_value("Большой чек не должен закрыться")
    expect(page.locator("#sessionRecoveryOverlay")).to_be_hidden()
    protected_result = page.evaluate(
        """
        () => window.App.core.requestJson('/api/v1/session-test/protected', {
          headers: window.App.core.authHeaders(),
        })
        """
    )
    assert protected_result == {"ok": True}
    assert counters["protected"] == 2
    assert counters["refresh"] == 2
    parallel_result = page.evaluate(
        """
        () => Promise.all([
          window.App.getRuntimeModule('session').refreshSession(),
          window.App.getRuntimeModule('session').refreshSession(),
        ])
        """
    )
    assert parallel_result == [True, True]
    assert counters["refresh"] == 3
    expect(page.locator("#createModal")).to_be_visible()
    expect(page.locator("#opNote")).to_have_value("Большой чек не должен закрыться")
    page.set_viewport_size({"width": 390, "height": 844})
    geometry = page.evaluate(
        """
        () => {
          const card = document.querySelector('#createModal .modal-card')?.getBoundingClientRect();
          const actions = document.querySelector('#createModal .modal-head-actions')?.getBoundingClientRect();
          return card && actions ? {
            cardLeft: card.left,
            cardRight: card.right,
            actionsLeft: actions.left,
            actionsRight: actions.right,
            bodyClientWidth: document.documentElement.clientWidth,
            bodyScrollWidth: document.documentElement.scrollWidth,
          } : null;
        }
        """
    )
    assert geometry is not None
    assert geometry["actionsLeft"] >= geometry["cardLeft"] - 1
    assert geometry["actionsRight"] <= geometry["cardRight"] + 1
    assert geometry["bodyScrollWidth"] <= geometry["bodyClientWidth"] + 1
    page.screenshot(path="/tmp/finasist-session-refresh-modal.png", full_page=True)
