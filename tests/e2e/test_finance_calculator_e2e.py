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
        page.route(
            "https://telegram.org/js/telegram-web-app.js*",
            lambda route: route.fulfill(status=200, content_type="application/javascript", body=""),
        )
        page.route("**/api/v1/**", handler)
        try:
            yield page
        finally:
            browser.close()


def _open_app(page, static_server_url: str):
    page.goto(f"{static_server_url}/static/index.html")
    page.wait_for_selector("#appShell:not(.hidden)")


@pytest.mark.e2e
def test_finance_calculator_modal_drawer_calculates_discount_without_horizontal_overflow(
    static_server_url: str,
    page_with_calculator_mock,
):
    page = page_with_calculator_mock
    page.set_viewport_size({"width": 390, "height": 844})
    _open_app(page, static_server_url)

    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.click("#createFinanceCalculatorToggle")
    page.wait_for_selector("#financeCalculatorDrawer:not(.hidden).modal-attached")
    page.click("#financeCalculatorInput-price")
    page.fill("#financeCalculatorInput-price", "100")
    page.click("#financeCalculatorInput-discount")
    page.fill("#financeCalculatorInput-discount", "15")

    expect(page.locator("#financeCalculatorResult")).to_contain_text("Итоговая цена")
    expect(page.locator("#financeCalculatorResult")).to_contain_text("85,00")
    expect(page.locator("#financeCalculatorResult")).to_contain_text("15,00")

    geometry = page.evaluate(
        """
        () => {
          const drawer = document.getElementById('financeCalculatorDrawer').getBoundingClientRect();
          const tabs = document.getElementById('financeCalculatorTabs').getBoundingClientRect();
          const splitTab = document.querySelector('[data-calculator-mode="split"]').getBoundingClientRect();
          return {
            top: drawer.top,
            bottom: drawer.bottom,
            width: drawer.width,
            height: drawer.height,
            clientWidth: document.getElementById('financeCalculatorDrawer').clientWidth,
            scrollWidth: document.getElementById('financeCalculatorDrawer').scrollWidth,
            overflowers: [...document.getElementById('financeCalculatorDrawer').querySelectorAll('*')]
              .map((node) => ({
                node: `${node.tagName}.${node.className}`,
                width: node.getBoundingClientRect().width,
                scrollWidth: node.scrollWidth,
                clientWidth: node.clientWidth,
              }))
              .filter((item) => item.scrollWidth > item.clientWidth),
            viewportWidth: window.innerWidth,
            viewportHeight: window.innerHeight,
            tabsRight: tabs.right,
            splitTabRight: splitTab.right,
          };
        }
        """
    )
    assert geometry["width"] <= geometry["viewportWidth"]
    assert geometry["bottom"] <= geometry["viewportHeight"] + 1
    assert geometry["height"] <= geometry["viewportHeight"] * 0.9
    assert geometry["scrollWidth"] <= geometry["clientWidth"], geometry["overflowers"]
    assert geometry["splitTabRight"] <= geometry["tabsRight"] + 1


@pytest.mark.e2e
def test_finance_calculator_attaches_to_operation_modal_without_global_overlay(static_server_url: str, page_with_calculator_mock):
    page = page_with_calculator_mock
    page.set_viewport_size({"width": 1440, "height": 900})
    _open_app(page, static_server_url)

    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.click("#createFinanceCalculatorToggle")
    page.wait_for_selector("#financeCalculatorDrawer:not(.hidden).modal-attached")

    assert page.locator("#financeCalculatorOverlay").evaluate("node => node.classList.contains('hidden')")
    page.click("#financeCalculatorInput-price")
    page.fill("#financeCalculatorInput-price", "200")
    page.click("#financeCalculatorInput-discount")
    page.fill("#financeCalculatorInput-discount", "10")
    expect(page.locator("#financeCalculatorResult")).to_contain_text("180,00")

    geometry = page.evaluate(
        """
        () => {
          const drawer = document.getElementById('financeCalculatorDrawer').getBoundingClientRect();
          const card = document.querySelector('#createModal .modal-card').getBoundingClientRect();
          const head = document.querySelector('#createModal .panel-head').getBoundingClientRect();
          const tabs = document.getElementById('financeCalculatorTabs').getBoundingClientRect();
          const splitTab = document.querySelector('[data-calculator-mode="split"]').getBoundingClientRect();
          return {
            drawerTop: drawer.top,
            drawerBottom: drawer.bottom,
            drawerLeft: drawer.left,
            drawerRight: drawer.right,
            cardTop: card.top,
            cardRight: card.right,
            headBottom: head.bottom,
            viewportWidth: window.innerWidth,
            viewportHeight: window.innerHeight,
            tabsRight: tabs.right,
            splitTabRight: splitTab.right,
          };
        }
        """
    )
    assert geometry["drawerTop"] >= geometry["headBottom"]
    assert geometry["drawerTop"] <= geometry["headBottom"] + 24
    assert geometry["drawerRight"] <= geometry["viewportWidth"] + 1
    assert geometry["drawerBottom"] <= geometry["viewportHeight"] + 1
    assert geometry["drawerLeft"] >= 0
    assert geometry["splitTabRight"] <= geometry["tabsRight"] + 1

    page.click("#closeCreateModalBtn")
    page.wait_for_function("() => document.querySelector('#financeCalculatorDrawer')?.classList.contains('hidden')")


@pytest.mark.e2e
@pytest.mark.parametrize("width", [320, 390, 1440])
@pytest.mark.parametrize("operation_mode", ["create", "edit"])
def test_calculator_receives_clicks_and_closes_without_losing_operation_draft(
    static_server_url: str, page_with_calculator_mock, width: int, operation_mode: str,
):
    page = page_with_calculator_mock
    page.set_viewport_size({"width": width, "height": 900})
    _open_app(page, static_server_url)
    if operation_mode == "create":
        page.click("#addOperationCta")
    else:
        page.evaluate("""() => window.App.getRuntimeModule('operation-modal').openEditModal({
          id: 1, kind: 'expense', amount: '2.99', original_amount: '2.99',
          currency: 'BYN', base_currency: 'BYN', operation_date: '2026-09-19',
          note: '', category_id: null, receipt_items: [],
        })""")
    modal = page.locator(f"#{operation_mode}Modal")
    note = page.locator("#opNote" if operation_mode == "create" else "#editNote")
    trigger = page.locator(f"#{operation_mode}FinanceCalculatorToggle")
    drawer = page.locator("#financeCalculatorDrawer")
    expect(modal).to_be_visible()
    note.fill("Несохранённая операция")

    for close_with_escape in [True, False]:
        trigger.click()
        expect(drawer).to_be_visible()
        price = page.locator("#financeCalculatorInput-price")
        price.click(timeout=2000)
        expect(price).to_be_focused()
        price.fill("100")
        page.click("#financeCalculatorInput-discount")
        page.fill("#financeCalculatorInput-discount", "15")
        expect(page.locator("#financeCalculatorResult")).to_contain_text("85,00")
        page.click('[data-calculator-mode="unit"]')
        page.click("#financeCalculatorInput-total")
        page.fill("#financeCalculatorInput-total", "12")
        page.click("#financeCalculatorInput-quantity")
        page.fill("#financeCalculatorInput-quantity", "3")
        expect(page.locator("#financeCalculatorResult")).to_contain_text("4,00")
        page.click('[data-calculator-mode="discount"]')
        if close_with_escape:
            page.keyboard.press("Escape")
        else:
            page.click("#financeCalculatorClose")
        expect(drawer).to_be_hidden()
        expect(modal).to_be_visible()
        expect(note).to_have_value("Несохранённая операция")
        expect(trigger).to_be_focused()
        expect(trigger).to_have_attribute("aria-expanded", "false")

    trigger.click()
    page.click(f"#close{operation_mode.capitalize()}ModalBtn")
    expect(modal).to_be_hidden()
    expect(drawer).to_be_hidden()


@pytest.mark.e2e
def test_calculator_respects_modal_stack_and_confirmation_above_it(
    static_server_url: str, page_with_calculator_mock,
):
    page = page_with_calculator_mock
    page.set_viewport_size({"width": 1440, "height": 900})
    _open_app(page, static_server_url)
    page.click("#addOperationCta")
    expect(page.locator("#createModal")).to_be_visible()
    # Simulate a long session with many nested windows; a fixed z-index is insufficient.
    page.evaluate("""() => {
      const modal = document.getElementById('createModal');
      for (let i = 0; i < 30; i += 1) window.App.core.bringModalToFront(modal);
    }""")
    page.click("#createFinanceCalculatorToggle")
    page.click("#financeCalculatorInput-price", timeout=2000)
    page.fill("#financeCalculatorInput-price", "100")
    page.evaluate("() => window.App.core.showConfirm('Проверка вложенного окна', () => {})")
    expect(page.locator("#confirmModal")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#confirmModal")).to_be_visible()
    expect(page.locator("#financeCalculatorDrawer")).to_be_visible()
    page.click("#confirmCancelBtn")
    expect(page.locator("#confirmModal")).to_be_hidden()
    page.click("#financeCalculatorInput-price")
    expect(page.locator("#financeCalculatorInput-price")).to_have_value("100")
    page.keyboard.press("Escape")
    expect(page.locator("#financeCalculatorDrawer")).to_be_hidden()
    expect(page.locator("#createModal")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#createModal")).to_be_hidden()
