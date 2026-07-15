from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sync_api = pytest.importorskip("playwright.sync_api", reason="playwright is not installed")
expect = sync_api.expect


def _set_mock_telegram(page):
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
    money_flow_queries = []
    currency_overview = {
        "base_currency": "BYN",
        "tracked_currencies": ["USD", "EUR"],
        "active_positions": 1,
        "total_book_value": "320.00",
        "total_current_value": "336.00",
        "total_result_value": "16.00",
        "buy_trades_count": 1,
        "sell_trades_count": 0,
        "buy_volume_base": "320.00",
        "sell_volume_base": "0.00",
        "buy_average_rate": "3.2000",
        "sell_average_rate": "0.0000",
        "positions": [
            {
                "currency": "USD",
                "quantity": "100.00",
                "average_buy_rate": "3.2000",
                "book_value": "320.00",
                "current_rate": "3.3600",
                "current_rate_date": "2026-03-28",
                "current_value": "336.00",
                "result_value": "16.00",
                "result_pct": 5.0,
                "realized_result_value": "0.00",
            }
        ],
        "recent_trades": [],
        "current_rates": [
            {
                "currency": "USD",
                "rate": "3.3600",
                "rate_date": "2026-03-28",
                "source": "manual",
                "previous_rate": "3.3400",
                "change_value": "0.0200",
                "change_pct": 0.6,
                "average_buy_rate": "3.2000",
                "average_sell_rate": "0.0000",
            },
            {
                "currency": "EUR",
                "rate": "3.5200",
                "rate_date": "2026-03-28",
                "source": "manual",
                "previous_rate": "3.5000",
                "change_value": "0.0200",
                "change_pct": 0.57,
                "average_buy_rate": "0.0000",
                "average_sell_rate": "0.0000",
            },
        ],
    }
    currency_history = {
        "USD": [
            {"currency": "USD", "rate": "3.3000", "rate_date": "2026-03-20"},
            {"currency": "USD", "rate": "3.3300", "rate_date": "2026-03-23"},
            {"currency": "USD", "rate": "3.3600", "rate_date": "2026-03-28"},
        ],
        "EUR": [
            {"currency": "EUR", "rate": "3.4400", "rate_date": "2026-03-20"},
            {"currency": "EUR", "rate": "3.4800", "rate_date": "2026-03-23"},
            {"currency": "EUR", "rate": "3.5200", "rate_date": "2026-03-28"},
        ],
    }
    history_fill_calls = []

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

    def highlights_payload(month: str, period: str = "month") -> dict:
        date_from = "2026-01-10" if period == "all_time" else f"{month}-01"
        date_to = "2026-06-16" if period == "all_time" else f"{month}-31"
        return {
            "period": period,
            "category_breakdown_kind": "expense",
            "date_from": date_from,
            "date_to": date_to,
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
                },
                {
                    "category_id": 2,
                    "category_name": "Транспорт",
                    "category_kind": "expense",
                    "total_amount": "670.00",
                    "total_expense": "670.00",
                    "share_pct": 55.4,
                    "operations_count": 12,
                    "change_pct": -4.0,
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
            "frequent_positions": [
                {"template_id": 11, "name": "Кофе зерновой", "shop_name": "Соседи", "purchases_count": 8, "quantity_total": "12.000", "amount_total": "84.60"},
                {"template_id": 12, "name": "Молоко", "shop_name": "Green", "purchases_count": 5, "quantity_total": "5.000", "amount_total": "20.00"},
            ],
            "price_increases": [
                {"name": "Кофе", "shop_name": "Соседи", "change_pct": 11.0, "previous_avg_unit_price": "9.00", "current_avg_unit_price": "10.00"}
            ],
            "top_discount_savings": [
                {
                    "name": "Капучино 0,2",
                    "shop_name": "Cofix",
                    "savings_total": "2.00",
                    "regular_total": "7.00",
                    "actual_total": "5.00",
                    "discount_pct": 28.57,
                    "quantity_total": "1.000",
                    "purchases_count": 1,
                }
            ],
        }

    def trend_payload(period: str, granularity: str, date_from: str = "2026-03-01", date_to: str = "2026-03-31") -> dict:
        return {
            "period": period,
            "granularity": granularity,
            "date_from": date_from,
            "date_to": date_to,
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

    def positions_payload(period: str, anchor: str = "2026-03-15") -> dict:
        if period == "year":
            labels = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
            buckets = [
                {
                    "key": f"2026-{month:02d}",
                    "label": label,
                    "date_from": f"2026-{month:02d}-01",
                    "date_to": f"2026-{month:02d}-28",
                }
                for month, label in enumerate(labels, start=1)
            ]
            date_from, date_to = "2026-01-01", "2026-12-31"
        elif period == "day":
            buckets = [{"key": "2026-03-15", "label": "15.03", "date_from": "2026-03-15", "date_to": "2026-03-15"}]
            date_from = date_to = "2026-03-15"
        elif period == "week":
            anchor_date = date.fromisoformat(anchor)
            week_start = anchor_date - timedelta(days=anchor_date.weekday())
            week_days = [week_start + timedelta(days=offset) for offset in range(7)]
            buckets = [
                {"key": day.isoformat(), "label": day.strftime("%d.%m"), "date_from": day.isoformat(), "date_to": day.isoformat()}
                for day in week_days
            ]
            date_from, date_to = week_days[0].isoformat(), week_days[-1].isoformat()
        else:
            buckets = [
                {"key": f"2026-03-{day:02d}", "label": str(day), "date_from": f"2026-03-{day:02d}", "date_to": f"2026-03-{day:02d}"}
                for day in range(1, 32)
            ]
            date_from, date_to = "2026-03-01", "2026-03-31"

        def values(active_indexes: set[int], quantity: int, amount: str) -> list[dict]:
            return [
                {
                    "key": bucket["key"],
                    "purchases_count": 1 if index in active_indexes else 0,
                    "quantity_total": str(quantity if index in active_indexes else 0),
                    "amount_total": amount if index in active_indexes else "0.00",
                }
                for index, bucket in enumerate(buckets)
            ]

        first_active = {0, min(4, len(buckets) - 1)}
        second_active = {min(2, len(buckets) - 1)}
        return {
            "period": period,
            "anchor": anchor,
            "date_from": date_from,
            "date_to": date_to,
            "buckets": buckets,
            "positions": [
                {
                    "template_id": 11,
                    "name": "Кофе зерновой",
                    "shop_name": "Соседи",
                    "purchases_count": len(first_active),
                    "quantity_total": str(len(first_active) * 2),
                    "amount_total": str(len(first_active) * 18),
                    "buckets": values(first_active, 2, "18.00"),
                },
                {
                    "template_id": 12,
                    "name": "Молоко",
                    "shop_name": "Green",
                    "purchases_count": len(second_active),
                    "quantity_total": str(len(second_active)),
                    "amount_total": str(len(second_active) * 4),
                    "buckets": values(second_active, 1, "4.00"),
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
            period = (query.get("period") or ["month"])[0]
            return json_response(route, highlights_payload(month, period))

        if path == "/api/v1/dashboard/analytics/trend" and method == "GET":
            period = (query.get("period") or ["month"])[0]
            granularity = (query.get("granularity") or ["day"])[0]
            date_from = (query.get("date_from") or ["2026-03-01"])[0]
            date_to = (query.get("date_to") or ["2026-03-31"])[0]
            return json_response(route, trend_payload(period, granularity, date_from, date_to))

        if path == "/api/v1/dashboard/analytics/positions" and method == "GET":
            period = (query.get("period") or ["month"])[0]
            anchor = (query.get("anchor") or ["2026-03-15"])[0]
            return json_response(route, positions_payload(period, anchor))

        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, [])

        if path == "/api/v1/currency/overview" and method == "GET":
            selected_currency = (query.get("currency") or ["all"])[0]
            if selected_currency and selected_currency != "all":
                payload = dict(currency_overview)
                payload["positions"] = [item for item in currency_overview["positions"] if item["currency"] == selected_currency]
                payload["current_rates"] = [item for item in currency_overview["current_rates"] if item["currency"] == selected_currency]
                payload["tracked_currencies"] = ["USD", "EUR"]
                payload["active_positions"] = len(payload["positions"])
                payload["total_book_value"] = payload["positions"][0]["book_value"] if payload["positions"] else "0.00"
                payload["total_current_value"] = payload["positions"][0]["current_value"] if payload["positions"] else "0.00"
                payload["total_result_value"] = payload["positions"][0]["result_value"] if payload["positions"] else "0.00"
                return json_response(route, payload)
            return json_response(route, currency_overview)

        if path == "/api/v1/currency/trades" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})

        if path == "/api/v1/currency/rates/history" and method == "GET":
            selected_currency = (query.get("currency") or ["USD"])[0]
            return json_response(route, currency_history.get(selected_currency, []))

        if path == "/api/v1/currency/rates/history/fill" and method == "POST":
            selected_currency = (query.get("currency") or ["USD"])[0]
            history_fill_calls.append(selected_currency)
            return json_response(route, currency_history.get(selected_currency, []), status=201)

        if path == "/api/v1/operations/money-flow" and method == "GET":
            money_flow_queries.append(query)
            return json_response(route, {
                "items": [
                    {
                        "id": "operation:1",
                        "source_kind": "operation",
                        "source_id": 1,
                        "flow_direction": "outflow",
                        "event_date": (query.get("date_from") or ["2026-03-01"])[0],
                        "amount": "80.00",
                        "original_amount": "80.00",
                        "currency": "BYN",
                        "base_currency": "BYN",
                        "fx_rate": "1.000000",
                        "title": "Еда",
                        "subtitle": "Обычная операция",
                        "category_id": int((query.get("category_id") or ["1"])[0]),
                        "category_name": "Еда",
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
            })

        if path == "/api/v1/operations/money-flow/summary" and method == "GET":
            return json_response(route, {
                "income_total": "0.00",
                "expense_total": "80.00",
                "balance": "-80.00",
                "total": 1,
            })

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

    _set_mock_telegram(page)
    page.route("**/api/v1/**", handler)
    page._currency_history_fill_calls = history_fill_calls
    page._analytics_money_flow_queries = money_flow_queries
    yield page


def _open_mobile_analytics(page, static_server_url: str):
    page.set_viewport_size({"width": 390, "height": 844})
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
    page.click("#mobileNavToggleBtn")
    page.click("button[data-section='analytics']")
    page.wait_for_selector("#analyticsSection:not(.hidden)")


def _open_desktop_app(page, static_server_url: str):
    page.set_viewport_size({"width": 1440, "height": 900})
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
def test_structure_donut_defaults_to_period_total_in_center(page_with_analytics_api_mock, static_server_url: str):
    page = page_with_analytics_api_mock

    _open_mobile_analytics(page, static_server_url)
    page.locator("button[data-analytics-tab='structure']").click()
    page.wait_for_selector("#analyticsStructurePanel:not(.hidden)")

    page.wait_for_selector("#analyticsCategoryBreakdownChartTitle")
    expect(page.locator("#analyticsCategoryBreakdownChartTitle")).to_have_text("Итог периода")
    expect(page.locator("#analyticsCategoryBreakdownChartValue")).to_contain_text("1\u00a0210,00")


@pytest.mark.e2e
def test_desktop_breakdown_lists_match_chart_height(page_with_analytics_api_mock, static_server_url: str):
    page = page_with_analytics_api_mock

    _open_desktop_app(page, static_server_url)
    page.wait_for_selector("#dashboardStructurePanel .analytics-category-breakdown-chart-card")
    page.wait_for_selector("#dashboardCategoryBreakdownList .analytics-insight-item")
    dashboard_geometry = page.evaluate(
        """
        () => {
          const chart = document.querySelector('#dashboardStructurePanel .analytics-category-breakdown-chart-card')?.getBoundingClientRect();
          const list = document.querySelector('#dashboardCategoryBreakdownList')?.getBoundingClientRect();
          return chart && list ? { chartHeight: chart.height, listHeight: list.height } : null;
        }
        """
    )
    assert dashboard_geometry is not None
    assert abs(dashboard_geometry["chartHeight"] - dashboard_geometry["listHeight"]) <= 1

    page.evaluate(
        """
        async () => {
          window.App.state.activeSection = 'analytics';
          window.App.state.analyticsTab = 'structure';
          document.getElementById('dashboardSection')?.classList.add('hidden');
          document.getElementById('analyticsSection')?.classList.remove('hidden');
          window.App.getRuntimeModule('analytics')?.applyAnalyticsTabUi?.();
          await window.App.getRuntimeModule('analytics')?.loadAnalyticsSection?.({ force: true });
        }
        """
    )
    page.wait_for_selector("#analyticsStructurePanel:not(.hidden)")
    page.wait_for_selector("#analyticsCategoryBreakdownList .analytics-insight-item")
    analytics_geometry = page.evaluate(
        """
        () => {
          const chart = document.querySelector('#analyticsStructurePanel .analytics-category-breakdown-chart-card')?.getBoundingClientRect();
          const list = document.querySelector('#analyticsCategoryBreakdownList')?.getBoundingClientRect();
          return chart && list ? { chartHeight: chart.height, listHeight: list.height } : null;
        }
        """
    )
    assert analytics_geometry is not None
    assert abs(analytics_geometry["chartHeight"] - analytics_geometry["listHeight"]) <= 1


@pytest.mark.e2e
def test_dashboard_position_ranking_routes_to_operations_and_full_analytics(page_with_analytics_api_mock, static_server_url: str):
    page = page_with_analytics_api_mock

    _open_desktop_app(page, static_server_url)
    page.evaluate("() => window.App.actions.switchSection('dashboard')")
    page.wait_for_selector("#dashboardPositionsRanking .analytics-position-ranking-row")
    expect(page.locator("#dashboardPositionsRanking .analytics-position-ranking-row")).to_have_count(2)
    expect(page.locator("#dashboardPositionsRanking")).to_contain_text("Кофе зерновой")
    expect(page.locator("#dashboardPositionsRanking")).to_contain_text("12.00")
    page.screenshot(path="/tmp/finasist-dashboard-ranking.png", full_page=True)

    page.locator("#dashboardPositionsRanking .analytics-position-ranking-row").first.click()
    page.wait_for_selector("#operationsSection:not(.hidden)")
    assert page.evaluate("() => window.App.state.operationsItemTemplateFilterId") == 11
    assert page.evaluate("() => window.App.state.period") == "custom"

    _open_desktop_app(page, static_server_url)
    page.evaluate("() => window.App.actions.switchSection('dashboard')")
    page.wait_for_selector("#dashboardPositionsRanking .analytics-position-ranking-row")
    page.locator("#openPositionsAnalyticsBtn").click()
    page.wait_for_selector("#analyticsPositionsPanel:not(.hidden)")
    assert page.evaluate("() => window.App.state.analyticsTab") == "positions"


@pytest.mark.e2e
def test_mobile_analytics_structure_shows_price_and_discount_insights(page_with_analytics_api_mock, static_server_url: str):
    page = page_with_analytics_api_mock

    _open_mobile_analytics(page, static_server_url)
    page.locator("button[data-analytics-tab='structure']").click()
    page.wait_for_selector("#analyticsStructurePanel:not(.hidden)")
    page.wait_for_selector("#analyticsPriceIncreasesList .analytics-insight-item")
    page.wait_for_selector("#analyticsTopDiscountSavingsList .analytics-insight-item")

    expect(page.locator(".analytics-price-insight-block").filter(has_text="Топ подорожаний")).to_contain_text("Кофе")
    expect(page.locator(".analytics-price-insight-block").filter(has_text="Топ подорожаний")).to_contain_text("+11.0%")
    expect(page.locator(".analytics-price-insight-block").filter(has_text="Лучшие скидки")).to_contain_text("Капучино 0,2")
    expect(page.locator(".analytics-price-insight-block").filter(has_text="Лучшие скидки")).to_contain_text("Скидка 28.6%")

    geometry = page.evaluate(
        """
        () => {
          const panel = document.querySelector('#analyticsStructurePanel');
          const blocks = Array.from(document.querySelectorAll('.analytics-price-insight-block'));
          if (!panel || blocks.length < 2) {
            return null;
          }
          const panelRect = panel.getBoundingClientRect();
          return {
            viewportWidth: window.innerWidth,
            panelRight: panelRect.right,
            maxBlockRight: Math.max(...blocks.map((item) => item.getBoundingClientRect().right)),
            minBlockWidth: Math.min(...blocks.map((item) => item.getBoundingClientRect().width)),
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["maxBlockRight"] <= geometry["viewportWidth"] + 2
    assert geometry["maxBlockRight"] <= geometry["panelRight"] + 2
    assert geometry["minBlockWidth"] > 280


@pytest.mark.e2e
def test_mobile_analytics_tabs_stay_above_period_controls(page_with_analytics_api_mock, static_server_url: str):
    page = page_with_analytics_api_mock

    _open_mobile_analytics(page, static_server_url)
    page.locator("button[data-analytics-tab='structure']").click()
    page.wait_for_selector("#analyticsStructurePanel:not(.hidden)")
    page.wait_for_selector("#analyticsGlobalScopePanel:not(.hidden)")

    geometry = page.evaluate(
        """
        () => {
          const tabs = document.querySelector('#analyticsViewTabs')?.getBoundingClientRect();
          const scope = document.querySelector('#analyticsGlobalScopePanel:not(.hidden)')?.getBoundingClientRect();
          if (!tabs || !scope) {
            return null;
          }
          return {
            tabsTop: tabs.top,
            tabsBottom: tabs.bottom,
            scopeTop: scope.top,
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["scopeTop"] >= geometry["tabsBottom"] - 1


@pytest.mark.e2e
def test_mobile_analytics_global_period_popover_changes_period(page_with_analytics_api_mock, static_server_url: str):
    page = page_with_analytics_api_mock

    _open_mobile_analytics(page, static_server_url)
    page.locator("button[data-analytics-tab='structure']").click()
    page.wait_for_selector("#analyticsStructurePanel:not(.hidden)")
    page.wait_for_selector("#analyticsGlobalScopePanel:not(.hidden)")
    page.locator("#analyticsGlobalPeriodTrigger").click()
    page.wait_for_selector("#analyticsGlobalPeriodPopover:not(.hidden)")
    page.locator("#analyticsGlobalPeriodPopover [data-analytics-period-choice='week']").click()
    page.wait_for_function("() => window.App.state.analyticsGlobalPeriod === 'week'")

    assert page.evaluate("() => window.App.state.analyticsGlobalPeriod") == "week"
    assert page.evaluate("() => window.App.state.analyticsGlobalDateFrom") == ""
    assert page.evaluate("() => window.App.state.analyticsGlobalDateTo") == ""


@pytest.mark.e2e
def test_mobile_analytics_structure_all_time_period_loads_without_error(page_with_analytics_api_mock, static_server_url: str):
    page = page_with_analytics_api_mock

    _open_mobile_analytics(page, static_server_url)
    page.locator("button[data-analytics-tab='structure']").click()
    page.wait_for_selector("#analyticsStructurePanel:not(.hidden)")
    page.locator("#analyticsGlobalPeriodTrigger").click()
    page.wait_for_selector("#analyticsGlobalPeriodPopover:not(.hidden)")
    page.locator("#analyticsGlobalPeriodPopover [data-analytics-period-choice='all_time']").click()
    page.wait_for_function("() => window.App.state.analyticsGlobalPeriod === 'all_time'")

    expect(page.locator("#analyticsGlobalPeriodControlLabel")).to_have_text("10.01.2026 - 16.06.2026")
    expect(page.locator("#analyticsCategoryBreakdownList .analytics-insight-item")).to_have_count(2)
    expect(page.locator(".toast, .status-error")).to_have_count(0)


@pytest.mark.e2e
def test_mobile_analytics_trend_period_arrows_update_visible_label(page_with_analytics_api_mock, static_server_url: str):
    page = page_with_analytics_api_mock

    _open_mobile_analytics(page, static_server_url)
    page.locator("button[data-analytics-tab='trends']").click()
    page.wait_for_selector("#analyticsTrendsPanel:not(.hidden)")
    expect(page.locator("#analyticsGlobalPeriodControlLabel")).to_have_text("01.03.2026 - 31.03.2026")

    page.locator("button[data-analytics-period-step='-1']").click()
    page.wait_for_function("() => window.App.state.analyticsGlobalPeriod === 'custom'")

    expect(page.locator("#analyticsGlobalPeriodControlLabel")).to_have_text("01.05.2026 - 31.05.2026")
    expect(page.locator("#analyticsTrendRangeLabel")).to_contain_text("01.05.2026 - 31.05.2026")


@pytest.mark.e2e
def test_mobile_position_analytics_renders_matrix_and_drills_into_operations(page_with_analytics_api_mock, static_server_url: str):
    page = page_with_analytics_api_mock

    _open_mobile_analytics(page, static_server_url)
    page.locator("button[data-analytics-tab='positions']").click()
    page.wait_for_selector("#analyticsPositionsPanel:not(.hidden)")
    page.wait_for_selector("#analyticsPositionsMatrixBody .analytics-position-cell.has-value")

    expect(page.locator("#analyticsPositionsSummary .analytics-position-kpi")).to_have_count(5)
    expect(page.locator("#analyticsPositionsSummary")).to_contain_text("Позиций")
    expect(page.locator("#analyticsPositionsMobileFocus")).to_contain_text("Кофе зерновой")
    page.locator("button[data-analytics-positions-metric='quantity']").click()
    expect(page.locator("#analyticsPositionsMobileFocus .analytics-positions-focus-head")).to_contain_text("4")

    page.locator("#analyticsPositionsPeriodTrigger").click()
    page.wait_for_selector("#analyticsPositionsPeriodPopover:not(.hidden)")
    page.locator("button[data-analytics-positions-period-choice='week']").click()
    page.wait_for_function("() => window.App.state.analyticsPositionsPeriod === 'week'")
    expect(page.locator("#analyticsPositionsRangeLabel")).not_to_have_text("Нет периода")
    expect(page.locator("#analyticsPositionsMobileFocus .analytics-position-focus-bar")).to_have_count(7)

    control_geometry = page.evaluate(
        """
        () => {
          const previous = document.getElementById('analyticsPositionsPrevBtn')?.getBoundingClientRect();
          const current = document.getElementById('analyticsPositionsPeriodTrigger')?.getBoundingClientRect();
          const next = document.getElementById('analyticsPositionsNextBtn')?.getBoundingClientRect();
          return previous && current && next ? {
            previousWidth: previous.width,
            currentWidth: current.width,
            nextWidth: next.width,
            previousHeight: previous.height,
            nextHeight: next.height,
          } : null;
        }
        """
    )
    assert control_geometry is not None
    assert abs(control_geometry["previousWidth"] - control_geometry["nextWidth"]) <= 1
    assert abs(control_geometry["previousHeight"] - control_geometry["nextHeight"]) <= 1
    assert control_geometry["currentWidth"] > control_geometry["previousWidth"]

    expect(page.locator("#analyticsPositionsRanking .analytics-position-ranking-row")).to_have_count(2)
    expect(page.locator("#analyticsPositionsRankingTitle")).to_have_text("Больше всего единиц")
    page.locator("#analyticsPositionsSortBtn").click()
    expect(page.locator("#analyticsPositionsRankingTitle")).to_have_text("Меньше всего единиц")
    expect(page.locator("#analyticsPositionsRanking .analytics-position-ranking-row").first).to_contain_text("Молоко")
    page.locator("#analyticsPositionsSortBtn").click()
    expect(page.locator("#analyticsPositionsRankingTitle")).to_have_text("Больше всего единиц")

    anchor_before_shift = date.fromisoformat(page.evaluate("() => window.App.state.analyticsPositionsAnchor"))
    page.locator("#analyticsPositionsPrevBtn").click()
    page.wait_for_function(
        "anchor => window.App.state.analyticsPositionsAnchor !== anchor",
        arg=anchor_before_shift.isoformat(),
    )
    anchor_after_shift = date.fromisoformat(page.evaluate("() => window.App.state.analyticsPositionsAnchor"))
    assert (anchor_before_shift - anchor_after_shift).days == 7

    geometry = page.evaluate(
        """
        () => {
          const panel = document.getElementById('analyticsPositionsPanel');
          const matrix = document.getElementById('analyticsPositionsMatrixWrap');
          const body = document.documentElement;
          if (!panel || !matrix) return null;
          const panelRect = panel.getBoundingClientRect();
          return {
            viewportWidth: window.innerWidth,
            panelLeft: panelRect.left,
            panelRight: panelRect.right,
            bodyClientWidth: body.clientWidth,
            bodyScrollWidth: body.scrollWidth,
            matrixClientWidth: matrix.clientWidth,
            matrixScrollWidth: matrix.scrollWidth,
          };
        }
        """
    )
    assert geometry is not None
    assert geometry["panelLeft"] >= -1
    assert geometry["panelRight"] <= geometry["viewportWidth"] + 1
    assert geometry["bodyScrollWidth"] <= geometry["bodyClientWidth"] + 1
    assert geometry["matrixScrollWidth"] > geometry["matrixClientWidth"]
    page.screenshot(path="/tmp/finasist-positions-mobile.png", full_page=True)

    page.locator("#analyticsPositionsMatrixBody .analytics-position-cell.has-value").first.click()
    page.wait_for_selector("#operationsSection:not(.hidden)")
    state = page.evaluate(
        """
        () => ({
          period: window.App.state.period,
          kind: window.App.state.filterKind,
          templateId: window.App.state.operationsItemTemplateFilterId,
          templateName: window.App.state.operationsItemTemplateFilterName,
        })
        """
    )
    assert state == {
        "period": "custom",
        "kind": "expense",
        "templateId": 11,
        "templateName": "Кофе зерновой",
    }


@pytest.mark.e2e
def test_desktop_position_analytics_keeps_sticky_columns_inside_panel(page_with_analytics_api_mock, static_server_url: str):
    page = page_with_analytics_api_mock

    _open_desktop_app(page, static_server_url)
    page.evaluate(
        """
        async () => {
          await window.App.actions.switchSection('analytics');
          window.App.actions.setAnalyticsTab('positions');
          await window.App.actions.loadAnalyticsPositions({ force: true });
        }
        """
    )
    page.wait_for_selector("#analyticsPositionsPanel:not(.hidden)")
    page.wait_for_selector("#analyticsPositionsMatrixBody .analytics-position-cell.has-value")

    geometry = page.evaluate(
        """
        () => {
          const panel = document.getElementById('analyticsPositionsPanel');
          const matrix = document.getElementById('analyticsPositionsMatrixWrap');
          const stickyName = matrix?.querySelector('.analytics-position-sticky-name');
          const stickyTotal = matrix?.querySelector('.analytics-position-sticky-total');
          if (!panel || !matrix || !stickyName || !stickyTotal) return null;
          matrix.scrollLeft = matrix.scrollWidth;
          const panelRect = panel.getBoundingClientRect();
          const matrixRect = matrix.getBoundingClientRect();
          const nameRect = stickyName.getBoundingClientRect();
          const totalRect = stickyTotal.getBoundingClientRect();
          return {
            panelLeft: panelRect.left,
            panelRight: panelRect.right,
            matrixLeft: matrixRect.left,
            matrixRight: matrixRect.right,
            nameLeft: nameRect.left,
            totalRight: totalRect.right,
            bodyClientWidth: document.documentElement.clientWidth,
            bodyScrollWidth: document.documentElement.scrollWidth,
          };
        }
        """
    )
    assert geometry is not None
    assert geometry["matrixLeft"] >= geometry["panelLeft"] - 1
    assert geometry["matrixRight"] <= geometry["panelRight"] + 1
    assert geometry["nameLeft"] >= geometry["matrixLeft"] - 1
    assert geometry["totalRight"] <= geometry["matrixRight"] + 1
    assert geometry["bodyScrollWidth"] <= geometry["bodyClientWidth"] + 1
    page.screenshot(path="/tmp/finasist-positions-desktop.png", full_page=True)


@pytest.mark.e2e
@pytest.mark.parametrize(("width", "height"), [(320, 720), (768, 900)])
def test_position_analytics_has_no_page_overflow_at_boundary_widths(
    page_with_analytics_api_mock,
    static_server_url: str,
    width: int,
    height: int,
):
    page = page_with_analytics_api_mock

    _open_mobile_analytics(page, static_server_url)
    page.evaluate("() => window.App.core.closeMobileNav()")
    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_timeout(250)
    page.locator("button[data-analytics-tab='positions']").click()
    page.wait_for_selector("#analyticsPositionsPanel:not(.hidden)")
    page.wait_for_selector("#analyticsPositionsMatrixBody .analytics-position-cell.has-value")

    geometry = page.evaluate(
        """
        () => {
          const panel = document.getElementById('analyticsPositionsPanel');
          const periodLabel = document.getElementById('analyticsPositionsPeriodControlLabel');
          const rect = panel?.getBoundingClientRect();
          return rect ? {
            left: rect.left,
            right: rect.right,
            viewportWidth: window.innerWidth,
            bodyClientWidth: document.documentElement.clientWidth,
            bodyScrollWidth: document.documentElement.scrollWidth,
            periodLabelClientWidth: periodLabel?.clientWidth || 0,
            periodLabelScrollWidth: periodLabel?.scrollWidth || 0,
          } : null;
        }
        """
    )
    assert geometry is not None
    assert geometry["left"] >= -1
    assert geometry["right"] <= geometry["viewportWidth"] + 1
    assert geometry["bodyScrollWidth"] <= geometry["bodyClientWidth"] + 1
    assert geometry["periodLabelScrollWidth"] <= geometry["periodLabelClientWidth"] + 1
    page.screenshot(path=f"/tmp/finasist-positions-{width}.png", full_page=True)


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

    _set_mock_telegram(page)
    page.route("**/api/v1/**", handler)
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
def test_analytics_calendar_highlights_current_day_and_month(static_server_url: str, page_with_analytics_api_mock):
    page = page_with_analytics_api_mock
    page.add_init_script(
        """
        (() => {
          const RealDate = Date;
          const fixedNow = new RealDate("2026-03-08T12:00:00");
          class MockDate extends RealDate {
            constructor(...args) {
              super(...(args.length ? args : [fixedNow.getTime()]));
            }
            static now() {
              return fixedNow.getTime();
            }
            static parse(value) {
              return RealDate.parse(value);
            }
            static UTC(...args) {
              return RealDate.UTC(...args);
            }
          }
          window.Date = MockDate;
        })();
        """
    )
    _open_mobile_analytics(page, static_server_url)

    page.click("button[data-analytics-tab='calendar']")
    page.wait_for_selector("#analyticsCalendarPanel:not(.hidden)")
    page.wait_for_selector(".analytics-day-cell-today button[data-analytics-date='2026-03-08']")

    page.click("button[data-analytics-calendar-view='year']")
    page.wait_for_selector("#analyticsYearGridWrap:not(.hidden)")
    page.wait_for_selector(".analytics-year-quarter[data-analytics-quarter='1']")
    assert page.locator(".analytics-year-quarter").count() == 4
    page.wait_for_selector(".analytics-year-card-current[data-analytics-month-anchor='2026-03']")


@pytest.mark.e2e
def test_analytics_calendar_month_picker_sizes_to_content(static_server_url: str, page_with_analytics_api_mock):
    page = page_with_analytics_api_mock
    _open_mobile_analytics(page, static_server_url)

    page.click("button[data-analytics-tab='calendar']")
    page.wait_for_selector("#analyticsCalendarPanel:not(.hidden)")
    page.click("#analyticsGridMonthTrigger")
    page.wait_for_selector("#analyticsGridMonthPopover:not(.hidden)")

    geometry = page.evaluate(
        """
        () => {
          const popover = document.getElementById('analyticsGridMonthPopover');
          const rect = popover.getBoundingClientRect();
          return {
            width: rect.width,
            right: rect.right,
            clientWidth: popover.clientWidth,
            scrollWidth: popover.scrollWidth,
            viewportWidth: window.innerWidth,
          };
        }
        """
    )

    assert geometry["width"] < 300, geometry
    assert geometry["right"] <= geometry["viewportWidth"] + 1
    assert geometry["scrollWidth"] <= geometry["clientWidth"]


@pytest.mark.e2e
def test_mobile_analytics_year_view_card_opens_month_view(static_server_url: str, page_with_analytics_api_mock):
    page = page_with_analytics_api_mock
    _open_mobile_analytics(page, static_server_url)

    page.click("button[data-analytics-tab='calendar']")
    page.wait_for_selector("#analyticsCalendarPanel:not(.hidden)")
    page.click("button[data-analytics-calendar-view='year']")
    page.wait_for_selector("#analyticsYearGridWrap:not(.hidden)")
    page.wait_for_selector(".analytics-year-quarter")
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


@pytest.mark.e2e
def test_mobile_analytics_category_drilldown_opens_operations_with_filter(
    static_server_url: str, page_with_analytics_api_mock
):
    page = page_with_analytics_api_mock
    _open_mobile_analytics(page, static_server_url)

    page.click("button[data-analytics-tab='structure']")
    page.wait_for_selector("#analyticsStructurePanel:not(.hidden)")
    page.wait_for_selector("#analyticsCategoryBreakdownList [data-analytics-category-id='1']")
    page.locator("#analyticsCategoryBreakdownList [data-analytics-category-id='1']", has_text="Еда").get_by_role(
        "button",
        name="Открыть операции",
    ).click()
    page.wait_for_selector("#operationsSection:not(.hidden)")
    page.wait_for_function("() => window.App.state.operationsCategoryFilterId === 1")

    state = page.evaluate(
        """
        () => ({
          activeSection: window.App.state.activeSection,
          period: window.App.state.period,
          categoryId: window.App.state.operationsCategoryFilterId,
          categoryName: window.App.state.operationsCategoryFilterName,
          kind: window.App.state.filterKind,
        })
        """
    )
    queries = page._analytics_money_flow_queries
    last_query = queries[-1] if queries else {}

    assert state["activeSection"] == "operations"
    assert state["period"] == "month"
    assert state["categoryId"] == 1
    assert state["categoryName"] == "Еда"
    assert state["kind"] == "expense"
    assert last_query.get("category_id") == ["1"]
    assert last_query.get("direction") == ["outflow"]


@pytest.mark.e2e
def test_currency_analytics_all_mode_renders_multi_currency_chart_and_backfill(page_with_analytics_api_mock, static_server_url: str):
    page = page_with_analytics_api_mock

    _open_mobile_analytics(page, static_server_url)
    page.locator("button[data-analytics-tab='currency']").click()
    page.wait_for_selector("#analyticsCurrencyPanel:not(.hidden)")
    page.wait_for_selector("button[data-analytics-currency-filter='all']")
    page.click("button[data-analytics-currency-filter='all']")
    page.click("button[data-analytics-currency-period='all_time']")
    page.wait_for_selector("#analyticsCurrencyChart .currency-chart-series")

    assert page.locator("#analyticsCurrencyBalancesRow .currency-balance-card").count() >= 3
    assert page.locator("#analyticsCurrencyChart .currency-chart-legend-label", has_text="USD").count() >= 1
    assert page.locator("#analyticsCurrencyChart .currency-chart-legend-label", has_text="EUR").count() >= 1
    assert page.locator("#analyticsCurrencyChart .currency-chart-series").count() >= 2
    chart_geometry = page.locator("#analyticsCurrencyChart").evaluate(
        """
        node => {
          const wrap = node.closest(".analytics-trend-chart-wrap");
          return {
            chartWidth: node.getBoundingClientRect().width,
            wrapWidth: wrap.getBoundingClientRect().width,
            scrollWidth: wrap.scrollWidth,
            clientWidth: wrap.clientWidth,
            overflowX: getComputedStyle(wrap).overflowX,
          };
        }
        """
    )
    assert chart_geometry["chartWidth"] > chart_geometry["wrapWidth"] + 80
    assert chart_geometry["scrollWidth"] > chart_geometry["clientWidth"] + 80
    assert chart_geometry["overflowX"] == "auto"

    page.click("#analyticsCurrencyBackfillBtn")
    page.wait_for_timeout(200)
    assert sorted(getattr(page, "_currency_history_fill_calls", [])) == ["EUR", "USD"]
