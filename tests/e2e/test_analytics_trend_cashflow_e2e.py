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
expect = sync_api.expect

from tests.e2e.test_analytics_mobile_e2e import _open_mobile_analytics, _restore_mock_telegram, _set_mock_telegram


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
def page_with_analytics_trend_cashflow_mock(page):
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"filters": {"kind": "", "q": ""}},
            "analytics": {
                "tab": "trends",
                "calendar_view": "month",
                "month_anchor": "2026-03",
                "summary_period": "month",
                "period": "month",
                "granularity": "day",
            },
            "ui": {"active_section": "dashboard", "timezone": "Europe/Minsk", "currency": "BYN", "currency_position": "suffix"},
        },
    }

    trend_payload = {
        "period": "month",
        "granularity": "day",
        "date_from": "2026-03-01",
        "date_to": "2026-03-31",
        "income_total": "1840.00",
        "expense_total": "1210.00",
        "balance": "630.00",
        "debt_cashflow_total": "-500.00",
        "fx_cashflow_total": "-300.00",
        "cashflow_total": "-170.00",
        "operations_count": 18,
        "prev_income_total": "1700.00",
        "prev_expense_total": "1250.00",
        "prev_balance": "450.00",
        "prev_debt_cashflow_total": "-200.00",
        "prev_fx_cashflow_total": "-100.00",
        "prev_cashflow_total": "150.00",
        "prev_operations_count": 16,
        "income_change_pct": 8.0,
        "expense_change_pct": -3.0,
        "balance_change_pct": 15.0,
        "debt_cashflow_change_pct": -150.0,
        "fx_cashflow_change_pct": -200.0,
        "cashflow_change_pct": -213.33,
        "operations_change_pct": 5.0,
        "points": [
            {
                "bucket_start": "2026-03-01",
                "bucket_end": "2026-03-07",
                "label": "01.03.2026",
                "income_total": "320.00",
                "expense_total": "190.00",
                "balance": "130.00",
                "debt_cashflow_total": "-120.00",
                "debt_events_count": 1,
                "fx_cashflow_total": "-80.00",
                "fx_events_count": 1,
                "cashflow_total": "-70.00",
                "cashflow_events_count": 6,
                "operations_count": 4,
            },
            {
                "bucket_start": "2026-03-08",
                "bucket_end": "2026-03-14",
                "label": "08.03.2026",
                "income_total": "450.00",
                "expense_total": "330.00",
                "balance": "120.00",
                "debt_cashflow_total": "-200.00",
                "debt_events_count": 2,
                "fx_cashflow_total": "-50.00",
                "fx_events_count": 1,
                "cashflow_total": "-130.00",
                "cashflow_events_count": 8,
                "operations_count": 5,
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
        if path == "/api/v1/auth/public-config" and method == "GET":
            return json_response(route, {"telegram_bot_username": "FinanceWeaselBot", "browser_login_available": True})
        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "Analytics User", "username": "analytics_user", "status": "approved", "is_admin": False})
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
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00", "cashflow_total": "0.00"})
        if path == "/api/v1/dashboard/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/dashboard/analytics" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/dashboard/analytics/calendar" and method == "GET":
            return json_response(
                route,
                {
                    "month": "2026-03",
                    "month_start": "2026-03-01",
                    "month_end": "2026-03-31",
                    "income_total": "100.00",
                    "expense_total": "50.00",
                    "balance": "50.00",
                    "cashflow_total": "50.00",
                    "operations_count": 2,
                    "weeks": [],
                },
            )
        if path == "/api/v1/dashboard/analytics/highlights" and method == "GET":
            return json_response(
                route,
                {
                    "period": "month",
                    "category_breakdown_kind": "expense",
                    "category_breakdown_level": "category",
                    "date_from": "2026-03-01",
                    "date_to": "2026-03-31",
                    "month": "2026-03",
                    "month_start": "2026-03-01",
                    "month_end": "2026-03-31",
                    "income_total": "1840.00",
                    "expense_total": "1210.00",
                    "balance": "630.00",
                    "debt_cashflow_total": "-500.00",
                    "fx_cashflow_total": "-300.00",
                    "cashflow_total": "-170.00",
                    "prev_income_total": "1700.00",
                    "prev_expense_total": "1250.00",
                    "prev_balance": "450.00",
                    "prev_debt_cashflow_total": "-200.00",
                    "prev_fx_cashflow_total": "-100.00",
                    "prev_cashflow_total": "150.00",
                    "prev_operations_count": 16,
                    "surplus_total": "0.00",
                    "deficit_total": "170.00",
                    "operations_count": 18,
                    "max_expense_day_total": "0.00",
                    "max_expense_day_date": None,
                    "income_change_pct": 8.0,
                    "expense_change_pct": -3.0,
                    "balance_change_pct": 15.0,
                    "debt_cashflow_change_pct": -150.0,
                    "fx_cashflow_change_pct": -200.0,
                    "cashflow_change_pct": -213.33,
                    "operations_change_pct": 5.0,
                    "category_breakdown": [],
                    "top_operations": [],
                    "anomalies": [],
                    "top_positions": [],
                    "price_increases": [],
                },
            )
        if path == "/api/v1/dashboard/analytics/trend" and method == "GET":
            return json_response(route, trend_payload)
        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/currency/overview" and method == "GET":
            return json_response(route, {"tracked_currencies": [], "positions": [], "recent_trades": [], "current_rates": [], "base_currency": "BYN", "total_result_value": "0.00"})
        if path == "/api/v1/currency/rates/history" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    _set_mock_telegram(page)
    page.route("**/api/v1/**", handler)
    yield page


@pytest.mark.e2e
def test_analytics_trend_uses_cashflow_total_for_result(page_with_analytics_trend_cashflow_mock, static_server_url: str):
    page = page_with_analytics_trend_cashflow_mock

    _open_mobile_analytics(page, static_server_url)
    page.locator("button[data-analytics-tab='trends']").click()
    page.wait_for_selector("#analyticsTrendsPanel:not(.hidden)")

    expect(page.locator("#analyticsResultLabel")).to_have_text("Денежный поток")
    expect(page.locator("#analyticsBalanceDelta")).to_have_text("-170,00\u00a0BYN")
    expect(page.locator("#analyticsTrendChart .trend-bucket")).to_have_count(2)
