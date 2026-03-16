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
def page_with_analytics_api_mock(page):
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"filters": {"kind": "", "q": ""}},
            "analytics": {
                "tab": "calendar",
                "calendar_view": "month",
                "month_anchor": "2026-03",
                "summary_period": "month",
                "period": "month",
                "granularity": "day",
            },
            "ui": {"active_section": "dashboard", "timezone": "Europe/Moscow"},
        },
    }

    operations_payload = {"items": [], "total": 0, "page": 1, "page_size": 20}

    def json_response(route, payload: dict | list, status: int = 200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def calendar_month_payload(month: str) -> dict:
        return {
            "month": month,
            "month_start": f"{month}-01",
            "month_end": f"{month}-31",
            "income_total": "1840.00",
            "expense_total": "1210.00",
            "balance": "630.00",
            "operations_count": 18,
            "weeks": [
                {
                    "week_start": f"{month}-03",
                    "week_end": f"{month}-09",
                    "income_total": "900.00",
                    "expense_total": "420.00",
                    "balance": "480.00",
                    "operations_count": 7,
                    "days": [
                        {
                            "date": f"{month}-{day:02d}",
                            "in_month": True,
                            "income_total": "120.00" if day in {3, 7} else "0.00",
                            "expense_total": "80.00" if day in {4, 8} else "15.00",
                            "balance": "40.00",
                            "operations_count": 2 if day == 8 else 1,
                        }
                        for day in range(3, 10)
                    ],
                },
                {
                    "week_start": f"{month}-10",
                    "week_end": f"{month}-16",
                    "income_total": "940.00",
                    "expense_total": "790.00",
                    "balance": "150.00",
                    "operations_count": 11,
                    "days": [
                        {
                            "date": f"{month}-{day:02d}",
                            "in_month": True,
                            "income_total": "220.00" if day == 12 else "0.00",
                            "expense_total": "60.00" if day != 14 else "250.00",
                            "balance": "10.00",
                            "operations_count": 2,
                        }
                        for day in range(10, 17)
                    ],
                },
            ],
        }

    def calendar_year_payload(year: int) -> dict:
        months = []
        for month in range(1, 13):
            months.append(
                {
                    "month": f"{year}-{month:02d}",
                    "income_total": f"{1000 + month * 10:.2f}",
                    "expense_total": f"{700 + month * 7:.2f}",
                    "balance": f"{300 + month * 3:.2f}",
                    "operations_count": 8 + month,
                }
            )
        return {
            "year": year,
            "year_start": f"{year}-01-01",
            "year_end": f"{year}-12-31",
            "income_total": "14400.00",
            "expense_total": "9600.00",
            "balance": "4800.00",
            "operations_count": 180,
            "months": months,
        }

    def highlights_payload(month: str) -> dict:
        return {
            "period": "month",
            "category_breakdown_kind": "expense",
            "date_from": f"{month}-01",
            "date_to": f"{month}-31",
            "month": month,
            "month_start": f"{month}-01",
            "month_end": f"{month}-31",
            "income_total": "1840.00",
            "expense_total": "1210.00",
            "balance": "630.00",
            "prev_income_total": "1700.00",
            "prev_expense_total": "1247.00",
            "prev_balance": "453.00",
            "prev_operations_count": 16,
            "operations_count": 18,
            "avg_daily_expense": "39.03",
            "max_expense_day_date": f"{month}-14",
            "max_expense_day_total": "250.00",
            "income_change_pct": 8.0,
            "expense_change_pct": -3.0,
            "balance_change_pct": 15.0,
            "operations_change_pct": 5.0,
            "category_breakdown": [
                {
                    "category_id": 1,
                    "category_name": "Еда",
                    "category_kind": "expense",
                    "total_amount": "540.00",
                    "total_expense": "540.00",
                    "share_pct": 44.6,
                    "operations_count": 6,
                    "change_pct": 12.0,
                }
            ],
            "top_operations": [
                {"amount": "250.00", "operation_date": f"{month}-14", "kind": "expense", "note": "Крупная покупка"}
            ],
            "top_categories": [
                {
                    "category_id": 1,
                    "category_name": "Еда",
                    "category_kind": "expense",
                    "total_amount": "540.00",
                    "total_expense": "540.00",
                    "share_pct": 44.6,
                    "operations_count": 6,
                    "change_pct": 12.0,
                }
            ],
            "anomalies": [
                {"amount": "250.00", "operation_date": f"{month}-14", "category_name": "Еда", "ratio_to_median": 2.8, "note": "Аномалия"}
            ],
            "top_positions": [
                {"name": "Кофе", "shop_name": "Соседи", "max_unit_price": "12.50", "purchases_count": 4, "total_spent": "41.50", "avg_unit_price": "10.38"}
            ],
            "price_increases": [
                {"name": "Кофе", "shop_name": "Соседи", "change_pct": 11.0, "previous_avg_unit_price": "9.00", "current_avg_unit_price": "10.00"}
            ],
        }

    def trend_payload(period: str, granularity: str) -> dict:
        return {
            "period": period,
            "granularity": granularity,
            "date_from": "2026-03-01",
            "date_to": "2026-03-31",
            "income_total": "1840.00",
            "expense_total": "1210.00",
            "balance": "630.00",
            "operations_count": 18,
            "prev_income_total": "1700.00",
            "prev_expense_total": "1250.00",
            "prev_balance": "450.00",
            "prev_operations_count": 16,
            "income_change_pct": 8.0,
            "expense_change_pct": -3.0,
            "balance_change_pct": 15.0,
            "operations_change_pct": 5.0,
            "points": [
                {
                    "bucket_start": "2026-03-01",
                    "bucket_end": "2026-03-07",
                    "income_total": "320.00",
                    "expense_total": "190.00",
                    "balance": "130.00",
                    "operations_count": 4,
                },
                {
                    "bucket_start": "2026-03-08",
                    "bucket_end": "2026-03-14",
                    "income_total": "450.00",
                    "expense_total": "330.00",
                    "balance": "120.00",
                    "operations_count": 5,
                },
            ],
        }

    def handler(route, request):
        nonlocal operations_payload
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
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00"})

        if path == "/api/v1/dashboard/operations" and method == "GET":
            return json_response(route, operations_payload)

        if path == "/api/v1/dashboard/analytics" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})

        if path == "/api/v1/dashboard/analytics/calendar" and method == "GET":
            month = (query.get("month") or ["2026-03"])[0]
            return json_response(route, calendar_month_payload(month))

        if path == "/api/v1/dashboard/analytics/calendar/year" and method == "GET":
            year = int((query.get("year") or ["2026"])[0])
            return json_response(route, calendar_year_payload(year))

        if path == "/api/v1/dashboard/analytics/highlights" and method == "GET":
            month = (query.get("month") or ["2026-03"])[0]
            return json_response(route, highlights_payload(month))

        if path == "/api/v1/dashboard/analytics/trend" and method == "GET":
            period = (query.get("period") or ["month"])[0]
            granularity = (query.get("granularity") or ["day"])[0]
            return json_response(route, trend_payload(period, granularity))

        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, [])

        if path == "/api/v1/operations" and method == "GET":
            if method == "GET":
                date_from = (query.get("date_from") or [""])[0]
                date_to = (query.get("date_to") or [""])[0]
                if date_from and date_to:
                    operations_payload = {
                        "items": [
                            {
                                "id": 1,
                                "kind": "expense",
                                "amount": "80.00",
                                "operation_date": date_from,
                                "category_id": None,
                                "note": "Операция из аналитики",
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "page_size": 20,
                    }
                return json_response(route, operations_payload)

        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

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
    yield page


def _open_mobile_analytics(page, static_server_url: str):
    page.set_viewport_size({"width": 390, "height": 844})
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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")
    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.click("#mobileNavToggleBtn")
    page.click("button[data-section='analytics']")
    page.wait_for_selector("#analyticsSection:not(.hidden)")


@pytest.mark.e2e
def test_opening_analytics_calendar_does_not_fail_when_other_tabs_endpoints_are_unavailable(page, static_server_url: str):
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"filters": {"kind": "", "q": ""}},
            "analytics": {
                "tab": "calendar",
                "calendar_view": "month",
                "month_anchor": "2026-03",
                "summary_period": "month",
                "period": "month",
                "granularity": "day",
            },
            "ui": {"active_section": "dashboard", "timezone": "Europe/Moscow"},
        },
    }

    def json_response(route, payload: dict | list, status: int = 200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def handler(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        method = request.method.upper()

        if path == "/api/v1/auth/telegram" and method == "POST":
            return json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})
        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "Analytics User", "username": "analytics_user", "status": "approved", "is_admin": False})
        if path == "/api/v1/preferences":
            if method == "GET":
                return json_response(route, preferences)
            if method == "PUT":
                return json_response(route, preferences)
        if path == "/api/v1/categories/groups" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/categories" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/dashboard/summary" and method == "GET":
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00"})
        if path == "/api/v1/dashboard/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/operations" and method == "GET":
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
                    "operations_count": 2,
                    "weeks": [],
                },
            )
        if path == "/api/v1/dashboard/analytics/highlights" and method == "GET":
            return json_response(route, {"detail": "highlights unavailable"}, status=503)
        if path == "/api/v1/dashboard/analytics/trend" and method == "GET":
            return json_response(route, {"detail": "trend unavailable"}, status=503)
        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")

    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.click("button[data-section='analytics']")
    page.wait_for_selector("#analyticsSection:not(.hidden)")
    page.wait_for_selector("#analyticsCalendarPanel:not(.hidden)")
    page.wait_for_timeout(150)

    assert page.locator(".toast-text:has-text('Не удалось открыть раздел «Аналитика»')").count() == 0
    assert page.locator("#analyticsMonthLabel").text_content().strip() != ""


@pytest.mark.e2e
def test_mobile_analytics_calendar_scroll_wrap_reaches_last_columns(static_server_url: str, page_with_analytics_api_mock):
    page = page_with_analytics_api_mock
    _open_mobile_analytics(page, static_server_url)

    page.click("button[data-analytics-tab='calendar']")
    page.wait_for_selector("#analyticsCalendarPanel:not(.hidden)")
    page.wait_for_selector("#analyticsCalendarBody .analytics-day-btn")

    geometry = page.evaluate(
        """
        () => {
          const wrap = document.querySelector('.analytics-calendar-scroll-wrap');
          const lastHeader = document.querySelector('#analyticsMonthGridWrap th:last-child');
          if (!wrap || !lastHeader) {
            return null;
          }
          wrap.scrollLeft = wrap.scrollWidth;
          const wrapRect = wrap.getBoundingClientRect();
          const headerRect = lastHeader.getBoundingClientRect();
          return {
            clientWidth: wrap.clientWidth,
            scrollWidth: wrap.scrollWidth,
            scrollLeft: wrap.scrollLeft,
            wrapRight: wrapRect.right,
            headerRight: headerRect.right,
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["scrollWidth"] > geometry["clientWidth"]
    assert geometry["scrollLeft"] > 0
    assert geometry["headerRight"] <= geometry["wrapRight"] + 2


@pytest.mark.e2e
def test_mobile_analytics_year_view_card_opens_month_view(static_server_url: str, page_with_analytics_api_mock):
    page = page_with_analytics_api_mock
    _open_mobile_analytics(page, static_server_url)

    page.click("button[data-analytics-tab='calendar']")
    page.wait_for_selector("#analyticsCalendarPanel:not(.hidden)")
    page.click("button[data-analytics-calendar-view='year']")
    page.wait_for_selector("#analyticsYearGridWrap:not(.hidden)")
    page.wait_for_selector("#analyticsYearGrid .analytics-year-card")
    page.click("#analyticsYearGrid .analytics-year-card")
    page.wait_for_selector("#analyticsMonthGridWrap:not(.hidden)")

    state = page.evaluate(
        """
        () => ({
          view: window.App.state.analyticsCalendarView,
          monthAnchor: window.App.state.analyticsMonthAnchor,
          monthWrapHidden: document.getElementById('analyticsMonthGridWrap')?.classList.contains('hidden'),
          yearWrapHidden: document.getElementById('analyticsYearGridWrap')?.classList.contains('hidden'),
        })
        """
    )

    assert state["view"] == "month"
    assert state["monthAnchor"] == "2026-01"
    assert state["monthWrapHidden"] is False
    assert state["yearWrapHidden"] is True


@pytest.mark.e2e
def test_mobile_analytics_day_tap_opens_operations_for_exact_date(static_server_url: str, page_with_analytics_api_mock):
    page = page_with_analytics_api_mock
    _open_mobile_analytics(page, static_server_url)

    page.click("button[data-analytics-tab='calendar']")
    page.wait_for_selector("#analyticsCalendarPanel:not(.hidden)")
    page.click("button[data-analytics-date='2026-03-08']")
    page.wait_for_selector("#operationsSection:not(.hidden)")

    state = page.evaluate(
        """
        () => ({
          activeSection: window.App.state.activeSection,
          period: window.App.state.period,
          dateFrom: window.App.state.customDateFrom,
          dateTo: window.App.state.customDateTo,
        })
        """
    )

    assert state["activeSection"] == "operations"
    assert state["period"] == "custom"
    assert state["dateFrom"] == "2026-03-08"
    assert state["dateTo"] == "2026-03-08"
