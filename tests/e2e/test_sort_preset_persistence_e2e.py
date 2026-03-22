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
def page_with_sort_prefs_api_mock():
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"filters": {"kind": "", "q": ""}, "sort_preset": "date"},
            "debts": {"sort_preset": "priority"},
            "ui": {"active_section": "dashboard", "timezone": "Europe/Moscow"},
        },
    }
    metrics = {"last_operations_sort_by_page20": ""}
    operations = [
        {"id": 1, "kind": "expense", "category_id": None, "amount": "10.00", "operation_date": "2026-03-05", "note": "A"},
        {"id": 2, "kind": "expense", "category_id": None, "amount": "200.00", "operation_date": "2026-03-04", "note": "B"},
    ]
    debt_cards = [
        {
            "counterparty_id": 1,
            "counterparty": "Зоя",
            "principal_total": "50.00",
            "repaid_total": "0.00",
            "outstanding_total": "50.00",
            "status": "active",
            "nearest_due_date": "2026-03-01",
            "debts": [
                {
                    "id": 9001,
                    "counterparty_id": 1,
                    "direction": "lend",
                    "principal": "50.00",
                    "repaid_total": "0.00",
                    "outstanding_total": "50.00",
                    "start_date": "2026-02-20",
                    "due_date": "2026-03-01",
                    "note": "Overdue",
                    "created_at": "2026-03-01T10:00:00Z",
                    "repayments": [],
                    "issuances": [],
                }
            ],
        },
        {
            "counterparty_id": 2,
            "counterparty": "Алина",
            "principal_total": "400.00",
            "repaid_total": "0.00",
            "outstanding_total": "400.00",
            "status": "active",
            "nearest_due_date": "2026-04-30",
            "debts": [
                {
                    "id": 9002,
                    "counterparty_id": 2,
                    "direction": "lend",
                    "principal": "400.00",
                    "repaid_total": "0.00",
                    "outstanding_total": "400.00",
                    "start_date": "2026-03-05",
                    "due_date": "2026-04-30",
                    "note": "Future",
                    "created_at": "2026-03-05T10:00:00Z",
                    "repayments": [],
                    "issuances": [],
                }
            ],
        },
    ]

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
            return json_response(route, {"id": 1, "display_name": "Sort User", "username": "sort_user", "status": "approved", "is_admin": False})
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
            if (query.get("page_size") or [""])[0] == "20":
                metrics["last_operations_sort_by_page20"] = (query.get("sort_by") or [""])[0]
            return json_response(route, {"items": operations, "total": len(operations), "page": 1, "page_size": 20})
        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, debt_cards)
        if path == "/api/v1/test/sort-metrics" and method == "GET":
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
def test_operations_sort_preset_persists_after_reload(static_server_url: str, page_with_sort_prefs_api_mock):
    page = page_with_sort_prefs_api_mock
    _open_app(page, static_server_url)
    page.click("button[data-section='operations']")
    page.wait_for_selector("#operationsSection:not(.hidden)")
    page.locator("#operationsSortTabs button[data-op-sort='amount']").click(force=True)
    page.wait_for_function(
        """
        () => document.querySelector('#operationsSortTabs .segmented-btn.active')?.dataset.opSort === 'amount'
        """
    )

    page.reload()
    _open_app(page, static_server_url)
    page.click("button[data-section='operations']")
    page.wait_for_selector("#operationsSection:not(.hidden)")
    page.wait_for_function(
        """
        () => document.querySelector('#operationsSortTabs .segmented-btn.active')?.dataset.opSort === 'amount'
        """
    )

    metrics = page.evaluate(
        """
        async () => {
          const response = await fetch('/api/v1/test/sort-metrics');
          return response.json();
        }
        """
    )
    assert metrics["last_operations_sort_by_page20"] == "amount"


@pytest.mark.e2e
def test_debts_sort_preset_persists_after_reload(static_server_url: str, page_with_sort_prefs_api_mock):
    page = page_with_sort_prefs_api_mock
    _open_app(page, static_server_url)
    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")

    first_before = page.locator("#debtsCards .debt-card h3").first.inner_text()
    assert first_before == "Зоя"

    page.locator("#debtSortTabs button[data-debt-sort='amount']").click(force=True)
    page.wait_for_function(
        """
        () => document.querySelector('#debtSortTabs .segmented-btn.active')?.dataset.debtSort === 'amount'
        """
    )
    first_after = page.locator("#debtsCards .debt-card h3").first.inner_text()
    assert first_after == "Алина"

    page.reload()
    _open_app(page, static_server_url)
    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.wait_for_function(
        """
        () => document.querySelector('#debtSortTabs .segmented-btn.active')?.dataset.debtSort === 'amount'
        """
    )
    first_after_reload = page.locator("#debtsCards .debt-card h3").first.inner_text()
    assert first_after_reload == "Алина"


@pytest.mark.e2e
def test_interface_currency_and_scale_persist_after_reload(static_server_url: str, page_with_sort_prefs_api_mock):
    page = page_with_sort_prefs_api_mock
    _open_app(page, static_server_url)
    page.click("button[data-section='settings']")
    page.wait_for_selector("#settingsSection:not(.hidden)")

    page.select_option("#currencySelect", "USD")
    page.select_option("#currencyPositionSelect", "prefix")
    page.evaluate(
        """
        () => {
          const scale = document.getElementById('uiScaleRange');
          scale.value = '92';
          scale.dispatchEvent(new Event('input', { bubbles: true }));
        }
        """
    )
    page.wait_for_timeout(900)

    page.reload()
    _open_app(page, static_server_url)
    page.click("button[data-section='settings']")
    page.wait_for_selector("#settingsSection:not(.hidden)")

    assert page.locator("#currencySelect").input_value() == "USD"
    assert page.locator("#currencyPositionSelect").input_value() == "prefix"
    assert page.locator("#uiScaleRange").input_value() == "92"
    assert "$" in page.locator("#currencyPreview").inner_text()
    assert "92%" in page.locator("#uiScaleValue").inner_text()
