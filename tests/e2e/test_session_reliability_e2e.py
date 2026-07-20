from __future__ import annotations

import base64
import json
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta
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
    counters = {"telegram_auth": 0, "refresh": 0, "protected": 0, "restore": 0}
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"filters": {"kind": "", "q": ""}},
            "ui": {"active_section": "dashboard", "timezone": "Europe/Minsk", "currency": "BYN", "currency_position": "suffix"},
        },
    }
    recent_time = (datetime.now().astimezone() - timedelta(minutes=3)).isoformat()
    older_time = (datetime.now().astimezone() - timedelta(minutes=8)).isoformat()

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
        if path == "/api/v1/activity" and method == "GET":
            items = [
                {
                    "id": 301,
                    "user_id": 1,
                    "actor_user_id": 1,
                    "entity_type": "operation",
                    "entity_id": 51,
                    "event_type": "updated",
                    "title": "Операция изменена",
                    "changes": [],
                    "metadata": {},
                    "metadata_display": [],
                    "entity_label": "Операция #51",
                    "entity_summary": "Расход · 15,89 BYN · 20.07.2026",
                    "entity_exists": True,
                    "available_actions": ["open", "edit"],
                    "source": "web",
                    "created_at": recent_time,
                },
                {
                    "id": 300,
                    "user_id": 1,
                    "actor_user_id": 1,
                    "entity_type": "operation",
                    "entity_id": 50,
                    "event_type": "deleted",
                    "title": "Операция удалена",
                    "changes": [],
                    "metadata": {},
                    "metadata_display": [],
                    "entity_label": "Операция #50",
                    "entity_summary": "Расход · 9,90 BYN · 20.07.2026",
                    "entity_exists": False,
                    "available_actions": ["details", "restore"],
                    "source": "web",
                    "created_at": older_time,
                },
            ]
            return json_response(route, {"items": items, "total": len(items)})
        if path == "/api/v1/operations/50/restore" and method == "POST":
            counters["restore"] += 1
            return json_response(route, {"id": 50})
        if path == "/api/v1/operations/51" and method == "GET":
            return json_response(route, {
                "id": 51,
                "amount": "15.89",
                "original_amount": "15.89",
                "currency": "BYN",
                "fx_rate": "1",
                "operation_date": "2026-07-20",
                "kind": "expense",
                "note": "",
                "category_id": None,
                "receipt_items": [],
                "fx_settlement": None,
            })
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
    currency_font = page.evaluate(
        """
        async () => {
          await document.fonts.ready;
          const probe = document.createElement('button');
          probe.textContent = `15,89\u00a0\ue901`;
          document.body.appendChild(probe);
          const result = {
            loaded: document.fonts.check('16px nbrb', '\ue901'),
            bodyFamily: getComputedStyle(document.body).fontFamily,
            buttonFamily: getComputedStyle(probe).fontFamily,
          };
          probe.remove();
          return result;
        }
        """
    )
    assert currency_font["loaded"] is True
    assert "nbrb" in currency_font["bodyFamily"]
    assert "nbrb" in currency_font["buttonFamily"]

    expect(page.locator("#sessionRemainingLabel")).to_contain_text("Осталось")
    expect(page.locator("#sessionStartedLabel")).to_contain_text("Начата")
    expect(page.locator("#sessionExpiresLabel")).to_contain_text("Завершится")
    initial_expiry_label = page.locator("#sessionExpiresLabel").inner_text()
    expect(page.locator("#sessionRenewedLabel")).to_be_hidden()
    session_geometry = page.evaluate(
        """
        () => {
          const panel = document.getElementById('sessionStatusRow')?.getBoundingClientRect();
          const user = document.querySelector('.user-block-static')?.getBoundingClientRect();
          const button = document.getElementById('sessionRefreshBtn')?.getBoundingClientRect();
          return panel && user && button ? {
            panelLeft: panel.left,
            panelRight: panel.right,
            panelBottom: panel.bottom,
            userLeft: user.left,
            userRight: user.right,
            userTop: user.top,
            buttonRight: button.right,
            buttonWidth: button.width,
          } : null;
        }
        """
    )
    assert session_geometry is not None
    assert session_geometry["buttonWidth"] <= 33
    assert abs(session_geometry["panelLeft"] - session_geometry["userLeft"]) <= 1
    assert abs(session_geometry["panelRight"] - session_geometry["userRight"]) <= 1
    assert session_geometry["panelBottom"] <= session_geometry["userTop"]
    assert session_geometry["buttonRight"] <= session_geometry["panelRight"]
    page.screenshot(path="/tmp/finasist-session-panel.png", full_page=True)
    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.fill("#opAmount", "129.90")
    page.fill("#opNote", "Большой чек не должен закрыться")
    page.click("#createSessionRefreshBtn")
    page.wait_for_function("() => document.getElementById('sessionRemainingLabel')?.textContent.includes('Осталось 30 мин')")

    assert counters["refresh"] == 1
    expect(page.locator("#sessionRenewedLabel")).to_be_visible()
    expect(page.locator("#sessionRenewedLabel")).to_contain_text("Обновлена")
    expect(page.locator("#sessionExpiresLabel")).not_to_have_text(initial_expiry_label)
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
    action_grouping = page.evaluate(
        """
        () => {
          const calculator = document.getElementById('createFinanceCalculatorToggle')?.getBoundingClientRect();
          const refresh = document.getElementById('createSessionRefreshBtn')?.getBoundingClientRect();
          const close = document.getElementById('closeCreateModalBtn')?.getBoundingClientRect();
          const calculatorStyle = document.getElementById('createFinanceCalculatorToggle')
            ? getComputedStyle(document.getElementById('createFinanceCalculatorToggle'))
            : null;
          const refreshStyle = document.getElementById('createSessionRefreshBtn')
            ? getComputedStyle(document.getElementById('createSessionRefreshBtn'))
            : null;
          return calculator && refresh && close && calculatorStyle && refreshStyle ? {
            contextualGap: refresh.left - calculator.right,
            systemGap: close.left - refresh.right,
            contextualColor: calculatorStyle.color,
            refreshColor: refreshStyle.color,
          } : null;
        }
        """
    )
    assert action_grouping is not None
    assert action_grouping["contextualGap"] > action_grouping["systemGap"]
    assert action_grouping["refreshColor"] != action_grouping["contextualColor"]
    page.set_viewport_size({"width": 390, "height": 844})
    geometry = page.evaluate(
        """
        () => {
          const card = document.querySelector('#createModal .modal-card')?.getBoundingClientRect();
          const actions = document.querySelector('#createModal .modal-head-actions')?.getBoundingClientRect();
          const actionButtons = Array.from(document.querySelectorAll('#createModal .modal-head-actions > button:not(.hidden)'))
            .map((button) => button.getBoundingClientRect());
          return card && actions ? {
            cardLeft: card.left,
            cardRight: card.right,
            actionsLeft: actions.left,
            actionsRight: actions.right,
            actionWidths: actionButtons.map((button) => button.width),
            actionHeights: actionButtons.map((button) => button.height),
            bodyClientWidth: document.documentElement.clientWidth,
            bodyScrollWidth: document.documentElement.scrollWidth,
          } : null;
        }
        """
    )
    assert geometry is not None
    assert geometry["actionsLeft"] >= geometry["cardLeft"] - 1
    assert geometry["actionsRight"] <= geometry["cardRight"] + 1
    assert all(abs(width - 34) <= 1 for width in geometry["actionWidths"])
    assert all(abs(height - 34) <= 1 for height in geometry["actionHeights"])
    assert geometry["bodyScrollWidth"] <= geometry["bodyClientWidth"] + 1
    page.screenshot(path="/tmp/finasist-session-refresh-modal.png", full_page=True)


@pytest.mark.e2e
def test_activity_center_desktop_mobile_and_restore(static_server_url: str, session_page):
    page, counters = session_page
    page.goto(f"{static_server_url}/static/index.html")
    page.wait_for_selector("#appShell:not(.hidden)")

    page.click("#activityCenterToggleBtn")
    page.wait_for_selector("#activityCenterDrawer:not(.hidden)")
    expect(page.locator("#activityCenterList .activity-center-event")).to_have_count(2)
    expect(page.locator("#activityCenterList")).to_contain_text("Операция изменена")
    expect(page.locator("#activityCenterList")).to_contain_text("Расход · 15,89 BYN")
    expect(page.locator('[data-activity-center-action="restore"]')).to_be_visible()
    desktop_geometry = page.evaluate(
        """
        () => {
          const drawer = document.getElementById('activityCenterDrawer')?.getBoundingClientRect();
          const overlay = document.getElementById('activityCenterOverlay');
          const rail = document.querySelector('.activity-rail')?.getBoundingClientRect();
          const trigger = document.getElementById('activityCenterToggleBtn')?.getBoundingClientRect();
          const main = document.querySelector('.main')?.getBoundingClientRect();
          return drawer && overlay && rail && trigger && main ? {
            left: drawer.left,
            right: drawer.right,
            top: drawer.top,
            bottom: drawer.bottom,
            railLeft: rail.left,
            railRight: rail.right,
            railWidth: rail.width,
            triggerLeft: trigger.left,
            triggerRight: trigger.right,
            triggerBottom: trigger.bottom,
            mainRight: main.right,
            overlayDisplay: getComputedStyle(overlay).display,
            viewportWidth: innerWidth,
            viewportHeight: innerHeight,
          } : null;
        }
        """
    )
    assert desktop_geometry is not None
    assert desktop_geometry["left"] >= 0
    assert desktop_geometry["right"] <= desktop_geometry["viewportWidth"]
    assert desktop_geometry["top"] >= 0
    assert desktop_geometry["bottom"] <= desktop_geometry["viewportHeight"]
    assert abs(desktop_geometry["railWidth"] - 52) <= 1
    assert abs(desktop_geometry["railRight"] - desktop_geometry["viewportWidth"]) <= 1
    assert desktop_geometry["mainRight"] <= desktop_geometry["railLeft"] + 1
    assert desktop_geometry["triggerLeft"] >= desktop_geometry["railLeft"]
    assert desktop_geometry["triggerRight"] <= desktop_geometry["railRight"]
    assert abs(desktop_geometry["top"] - desktop_geometry["triggerBottom"] - 9) <= 1
    assert desktop_geometry["overlayDisplay"] == "none"
    footer_geometry = page.evaluate(
        """
        () => {
          const drawer = document.getElementById('activityCenterDrawer')?.getBoundingClientRect();
          const footer = document.querySelector('.activity-center-footer')?.getBoundingClientRect();
          const button = document.getElementById('activityCenterAllBtn')?.getBoundingClientRect();
          return drawer && footer && button ? {
            drawerBottom: drawer.bottom,
            footerBottom: footer.bottom,
            buttonBottom: button.bottom,
          } : null;
        }
        """
    )
    assert footer_geometry is not None
    assert footer_geometry["footerBottom"] <= footer_geometry["drawerBottom"] + 1
    assert footer_geometry["buttonBottom"] <= footer_geometry["footerBottom"] + 1
    page.screenshot(path="/tmp/finasist-activity-center-desktop.png", full_page=True)

    page.click("#activityCenterAllBtn")
    page.wait_for_selector("#activityModal:not(.hidden)")
    expect(page.locator("#activityModalSubtitle")).to_have_text("Все изменения по разделам")
    expect(page.locator('[data-activity-modal-event-id="301"]')).to_have_css("cursor", "pointer")
    expect(page.locator('#activityList [data-activity-center-action="restore"]')).to_be_visible()
    page.locator('[data-activity-modal-event-id="301"]').hover()
    history_geometry = page.evaluate(
        """
        () => {
          const list = document.getElementById('activityList')?.getBoundingClientRect();
          const first = document.querySelector('#activityList .activity-event')?.getBoundingClientRect();
          return list && first ? { listTop: list.top, firstTop: first.top } : null;
        }
        """
    )
    assert history_geometry is not None
    assert history_geometry["firstTop"] >= history_geometry["listTop"] + 1
    page.screenshot(path="/tmp/finasist-activity-history-modal.png", full_page=True)
    page.click('[data-activity-modal-event-id="300"]')
    expect(page.locator("#activityModalSubtitle")).to_have_text("История операции")
    page.click("#closeActivityModalBtn")
    page.click("#activityCenterToggleBtn")
    page.wait_for_selector("#activityCenterDrawer:not(.hidden)")
    page.click('[data-activity-center-event-id="301"][data-activity-center-action="open"]')
    page.wait_for_selector("#editModal:not(.hidden)")
    expect(page.locator("#activityCenterDrawer")).to_be_visible()
    expect(page.locator("#activityCenterDrawer")).not_to_have_class("hidden")
    page.click("#closeEditModalBtn")
    page.click('#activityCenterList [data-activity-center-action="restore"]')
    page.wait_for_selector("#confirmModal:not(.hidden)")
    expect(page.locator("#confirmTitle")).to_have_text("Восстановление")
    page.click("#confirmDeleteBtn")
    page.wait_for_function("() => document.querySelector('#confirmModal')?.classList.contains('hidden')")
    assert counters["restore"] == 1
    expect(page.locator(".toast-activity-btn")).to_be_visible()

    page.click("#activityCenterCloseBtn")
    toast_geometry = page.evaluate(
        """
        () => {
          const toast = document.querySelector('.toast-area')?.getBoundingClientRect();
          const rail = document.querySelector('.activity-rail')?.getBoundingClientRect();
          return toast && rail ? {
            toastRight: toast.right,
            railLeft: rail.left,
          } : null;
        }
        """
    )
    assert toast_geometry is not None
    assert toast_geometry["toastRight"] <= toast_geometry["railLeft"] - 12
    page.evaluate("() => document.dispatchEvent(new CustomEvent('app:activity-changed'))")
    expect(page.locator("#activityCenterBadge")).to_be_visible()

    page.set_viewport_size({"width": 390, "height": 844})
    page.click("#activityCenterToggleBtn")
    page.wait_for_selector("#activityCenterDrawer:not(.hidden)")
    mobile_geometry = page.evaluate(
        """
        () => {
          const drawer = document.getElementById('activityCenterDrawer')?.getBoundingClientRect();
          const overlay = document.getElementById('activityCenterOverlay');
          const rail = document.querySelector('.activity-rail')?.getBoundingClientRect();
          return drawer && overlay && rail ? {
            left: drawer.left,
            right: drawer.right,
            bottom: drawer.bottom,
            overlayDisplay: getComputedStyle(overlay).display,
            viewportWidth: innerWidth,
            viewportHeight: innerHeight,
            bodyClientWidth: document.documentElement.clientWidth,
            bodyScrollWidth: document.documentElement.scrollWidth,
            railWidth: rail.width,
            railRight: rail.right,
          } : null;
        }
        """
    )
    assert mobile_geometry is not None
    assert abs(mobile_geometry["left"]) <= 1
    assert abs(mobile_geometry["right"] - mobile_geometry["viewportWidth"]) <= 1
    assert abs(mobile_geometry["bottom"] - mobile_geometry["viewportHeight"]) <= 1
    assert mobile_geometry["overlayDisplay"] == "block"
    assert abs(mobile_geometry["railWidth"] - 34) <= 1
    assert mobile_geometry["railRight"] <= mobile_geometry["viewportWidth"] + 1
    assert mobile_geometry["bodyScrollWidth"] <= mobile_geometry["bodyClientWidth"] + 1
    page.screenshot(path="/tmp/finasist-activity-center-mobile.png", full_page=True)
