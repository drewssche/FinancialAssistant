from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sync_api = pytest.importorskip("playwright.sync_api", reason="playwright is not installed")


def _json_response(route, payload: dict | list, status: int = 200):
    route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))


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


def _month_last_day(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - date.resolution).day


def _advance_monthly(iso_date: str, interval: int, month_end: bool) -> str:
    scheduled = date.fromisoformat(iso_date)
    month_index = (scheduled.month - 1) + interval
    year = scheduled.year + (month_index // 12)
    month = (month_index % 12) + 1
    last_day = _month_last_day(year, month)
    day = last_day if month_end else min(scheduled.day, last_day)
    return date(year, month, day).isoformat()


def _advance_weekly(iso_date: str, interval: int, weekdays: list[int]) -> str:
    scheduled = date.fromisoformat(iso_date)
    normalized = sorted(set(int(value) for value in weekdays))
    current_weekday = scheduled.weekday()
    for weekday in normalized:
        if weekday > current_weekday:
            return date.fromordinal(scheduled.toordinal() + (weekday - current_weekday)).isoformat()
    start_of_week = date.fromordinal(scheduled.toordinal() - current_weekday)
    next_cycle_start = date.fromordinal(start_of_week.toordinal() + (7 * interval))
    return date.fromordinal(next_cycle_start.toordinal() + normalized[0]).isoformat()


def _advance_daily_workdays(iso_date: str, interval: int) -> str:
    current = date.fromisoformat(iso_date)
    remaining = max(1, int(interval))
    while remaining > 0:
        current = date.fromordinal(current.toordinal() + 1)
        if current.weekday() >= 5:
            continue
        remaining -= 1
    return current.isoformat()


def _recurrence_label(payload: dict) -> str:
    if not payload.get("recurrence_enabled"):
        return "Разовый"
    frequency = payload.get("recurrence_frequency")
    interval = int(payload.get("recurrence_interval") or 1)
    if frequency == "weekly":
        weekday_labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        weekdays = payload.get("recurrence_weekdays") or []
        base = "Еженедельно"
        if weekdays:
            base = f"{base}: {', '.join(weekday_labels[idx] for idx in weekdays)}"
    elif frequency == "monthly":
        base = "Ежемесячно"
        if payload.get("recurrence_month_end"):
            base = f"{base}: в последний день месяца"
    elif frequency == "daily":
        base = "По будням" if payload.get("recurrence_workdays_only") else "Ежедневно"
    elif frequency == "yearly":
        base = "Ежегодно"
    else:
        base = "Регулярно"
    if interval <= 1:
        return base
    return f"{base}, шаг {interval}"


def _make_plan_item(plan: dict) -> dict:
    return {
        "id": plan["id"],
        "kind": plan["kind"],
        "amount": plan["amount"],
        "scheduled_date": plan["scheduled_date"],
        "due_date": plan["scheduled_date"],
        "category_id": None,
        "category_name": None,
        "category_icon": None,
        "category_accent_color": None,
        "note": plan.get("note"),
        "receipt_items": [],
        "receipt_total": None,
        "recurrence_enabled": bool(plan.get("recurrence_enabled")),
        "recurrence_frequency": plan.get("recurrence_frequency"),
        "recurrence_interval": int(plan.get("recurrence_interval") or 1),
        "recurrence_weekdays": list(plan.get("recurrence_weekdays") or []),
        "recurrence_workdays_only": bool(plan.get("recurrence_workdays_only")),
        "recurrence_month_end": bool(plan.get("recurrence_month_end")),
        "recurrence_end_date": plan.get("recurrence_end_date"),
        "recurrence_label": _recurrence_label(plan),
        "status": plan.get("status", "upcoming"),
        "progress_anchor_at": plan.get("progress_anchor_at") or plan.get("created_at") or "2026-03-16T12:00:00Z",
        "next_reminder_at": plan.get("next_reminder_at"),
        "confirmed_operation_id": plan.get("confirmed_operation_id"),
        "confirm_count": int(plan.get("confirm_count") or 0),
        "skip_count": int(plan.get("skip_count") or 0),
        "last_confirmed_at": plan.get("last_confirmed_at"),
        "last_skipped_at": plan.get("last_skipped_at"),
        "created_at": plan.get("created_at") or "2026-03-16T12:00:00Z",
    }


@pytest.fixture()
def page_with_plans_api_mock(page):
    mock_state = {
        "plans": [],
        "history": [],
        "operations": [],
        "last_create_payload": None,
        "next_plan_id": 1,
        "next_operation_id": 100,
        "preferences": {
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
                "plans": {"status_filter": "all", "reminders_enabled": True},
                "ui": {"active_section": "dashboard", "timezone": "Europe/Moscow"},
            },
        },
    }

    def handler(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        query = parse_qs(parsed.query)
        method = request.method.upper()

        if path == "/api/v1/auth/public-config":
            return _json_response(route, {"telegram_bot_username": None, "browser_login_available": False})
        if path == "/api/v1/auth/telegram" and method == "POST":
            return _json_response(route, {"access_token": "plans-e2e-token", "token_type": "bearer"})
        if path == "/api/v1/users/me" and method == "GET":
            return _json_response(
                route,
                {
                    "id": 1,
                    "display_name": "Plans UI",
                    "username": "plans_ui",
                    "telegram_id": "880011",
                    "status": "approved",
                    "is_admin": False,
                },
            )
        if path == "/api/v1/preferences":
            if method == "GET":
                return _json_response(route, mock_state["preferences"])
            if method == "PUT":
                payload = json.loads(request.post_data or "{}")
                mock_state["preferences"] = payload
                return _json_response(route, payload)
        if path == "/api/v1/categories/groups" and method == "GET":
            return _json_response(route, [])
        if path == "/api/v1/categories" and method == "GET":
            if "page" in query and "page_size" in query:
                return _json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
            return _json_response(route, [])
        if path == "/api/v1/dashboard/summary" and method == "GET":
            return _json_response(
                route,
                {
                    "income_total": "0.00",
                    "expense_total": "0.00",
                    "balance": "0.00",
                    "debt_lend_total": "0.00",
                    "debt_borrow_total": "0.00",
                    "debt_net_total": "0.00",
                },
            )
        if path == "/api/v1/dashboard/operations" and method == "GET":
            return _json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/dashboard/analytics" and method == "GET":
            return _json_response(route, {"points": [], "summary": {}})
        if path == "/api/v1/dashboard/analytics/calendar" and method == "GET":
            month = query.get("month", ["2026-03"])[0]
            return _json_response(
                route,
                {
                    "month": month,
                    "month_start": f"{month}-01",
                    "month_end": f"{month}-31",
                    "income_total": "0.00",
                    "expense_total": "0.00",
                    "balance": "0.00",
                    "operations_count": 0,
                    "weeks": [],
                },
            )
        if path == "/api/v1/dashboard/analytics/calendar/year" and method == "GET":
            year = int(query.get("year", ["2026"])[0])
            return _json_response(
                route,
                {
                    "year": year,
                    "year_start": f"{year}-01-01",
                    "year_end": f"{year}-12-31",
                    "income_total": "0.00",
                    "expense_total": "0.00",
                    "balance": "0.00",
                    "operations_count": 0,
                    "months": [],
                },
            )
        if path == "/api/v1/dashboard/analytics/highlights" and method == "GET":
            return _json_response(
                route,
                {
                    "period": "month",
                    "category_breakdown_kind": "expense",
                    "date_from": "2026-03-01",
                    "date_to": "2026-03-31",
                    "month": "2026-03",
                    "month_start": "2026-03-01",
                    "month_end": "2026-03-31",
                    "income_total": "0.00",
                    "expense_total": "0.00",
                    "balance": "0.00",
                    "prev_income_total": "0.00",
                    "prev_expense_total": "0.00",
                    "prev_balance": "0.00",
                    "prev_operations_count": 0,
                    "operations_count": 0,
                    "avg_daily_expense": "0.00",
                    "category_breakdown": [],
                    "top_operations": [],
                    "top_categories": [],
                    "anomalies": [],
                    "top_positions": [],
                    "price_increases": [],
                },
            )
        if path == "/api/v1/dashboard/analytics/trend" and method == "GET":
            return _json_response(
                route,
                {
                    "period": "month",
                    "granularity": "day",
                    "date_from": "2026-03-01",
                    "date_to": "2026-03-31",
                    "income_total": "0.00",
                    "expense_total": "0.00",
                    "balance": "0.00",
                    "operations_count": 0,
                    "prev_income_total": "0.00",
                    "prev_expense_total": "0.00",
                    "prev_balance": "0.00",
                    "prev_operations_count": 0,
                    "points": [],
                },
            )
        if path == "/api/v1/operations" and method == "GET":
            return _json_response(route, {"items": mock_state["operations"], "total": len(mock_state["operations"]), "page": 1, "page_size": 20})
        if path == "/api/v1/debts/cards" and method == "GET":
            return _json_response(route, [])
        if path == "/api/v1/plans" and method == "GET":
            return _json_response(route, {"items": [_make_plan_item(item) for item in mock_state["plans"]], "total": len(mock_state["plans"])})
        if path == "/api/v1/plans/history" and method == "GET":
            return _json_response(route, {"items": list(mock_state["history"]), "total": len(mock_state["history"])})
        if path == "/api/v1/plans" and method == "POST":
            payload = json.loads(request.post_data or "{}")
            mock_state["last_create_payload"] = payload
            plan = {
                "id": mock_state["next_plan_id"],
                "kind": payload["kind"],
                "amount": payload["amount"],
                "scheduled_date": payload["scheduled_date"],
                "note": payload.get("note"),
                "recurrence_enabled": bool(payload.get("recurrence_enabled")),
                "recurrence_frequency": payload.get("recurrence_frequency"),
                "recurrence_interval": int(payload.get("recurrence_interval") or 1),
                "recurrence_weekdays": list(payload.get("recurrence_weekdays") or []),
                "recurrence_workdays_only": bool(payload.get("recurrence_workdays_only")),
                "recurrence_month_end": bool(payload.get("recurrence_month_end")),
                "recurrence_end_date": payload.get("recurrence_end_date"),
                "status": "upcoming",
                "confirm_count": 0,
                "skip_count": 0,
                "confirmed_operation_id": None,
                "created_at": "2026-03-16T12:00:00Z",
                "next_reminder_at": "2026-03-17T06:00:00Z",
            }
            mock_state["next_plan_id"] += 1
            mock_state["plans"].append(plan)
            return _json_response(route, _make_plan_item(plan), status=201)
        if path.startswith("/api/v1/plans/") and path.endswith("/confirm") and method == "POST":
            plan_id = int(path.split("/")[-2])
            plan = next(item for item in mock_state["plans"] if int(item["id"]) == plan_id)
            operation_id = mock_state["next_operation_id"]
            mock_state["next_operation_id"] += 1
            operation = {
                "id": operation_id,
                "kind": plan["kind"],
                "amount": plan["amount"],
                "operation_date": plan["scheduled_date"],
                "note": plan.get("note"),
            }
            mock_state["operations"].insert(0, operation)
            mock_state["history"].insert(
                0,
                {
                    "id": len(mock_state["history"]) + 1,
                    "plan_id": plan_id,
                    "operation_id": operation_id,
                    "event_type": "confirmed",
                    "kind": plan["kind"],
                    "amount": plan["amount"],
                    "effective_date": plan["scheduled_date"],
                    "note": plan.get("note"),
                    "category_name": None,
                    "created_at": "2026-03-16T12:05:00Z",
                },
            )
            plan["confirmed_operation_id"] = operation_id
            plan["confirm_count"] = int(plan.get("confirm_count") or 0) + 1
            plan["last_confirmed_at"] = "2026-03-16T12:05:00Z"
            if plan.get("recurrence_enabled"):
                if plan.get("recurrence_frequency") == "daily" and plan.get("recurrence_workdays_only"):
                    plan["scheduled_date"] = _advance_daily_workdays(
                        plan["scheduled_date"],
                        int(plan.get("recurrence_interval") or 1),
                    )
                elif plan.get("recurrence_frequency") == "monthly":
                    plan["scheduled_date"] = _advance_monthly(
                        plan["scheduled_date"],
                        int(plan.get("recurrence_interval") or 1),
                        bool(plan.get("recurrence_month_end")),
                    )
                elif plan.get("recurrence_frequency") == "weekly":
                    plan["scheduled_date"] = _advance_weekly(
                        plan["scheduled_date"],
                        int(plan.get("recurrence_interval") or 1),
                        list(plan.get("recurrence_weekdays") or [0]),
                    )
                plan["status"] = "upcoming"
            else:
                plan["status"] = "confirmed"
            return _json_response(route, {"plan": _make_plan_item(plan), "operation": operation})
        return _json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    _set_mock_telegram(page)
    page.route("**/api/v1/**", handler)
    return page, mock_state


def _login_and_open_plans(page, static_server_url: str):
    page.goto(f"{static_server_url}/static/index.html")
    _restore_mock_telegram(page)
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")
    try:
        page.locator("#telegramLoginBtn").wait_for(state="visible", timeout=1200)
        page.click("#telegramLoginBtn")
        page.wait_for_selector("#appShell:not(.hidden)")
    except Exception:
        page.wait_for_selector("#appShell:not(.hidden)")
    page.click('button[data-section="plans"]')
    page.wait_for_selector("#plansSection:not(.hidden)")
    page.wait_for_selector("#addPlanCta:not(.hidden)")


def _wait_for_history_pref(mock_state: dict, expected: str, timeout_sec: float = 3.0):
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        current = ((mock_state.get("preferences") or {}).get("data") or {}).get("plans", {}).get("history_event_filter")
        if current == expected:
            return
        time.sleep(0.05)
    raise AssertionError(f"history_event_filter did not become {expected!r}")


@pytest.mark.e2e
def test_plans_ui_creates_weekly_multiweekday_plan(static_server_url: str, page_with_plans_api_mock):
    page, mock_state = page_with_plans_api_mock
    _login_and_open_plans(page, static_server_url)

    page.click("#addPlanCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.fill("#opDate", "2026-03-09")
    page.fill("#opAmount", "20")
    page.fill("#opNote", "Спортзал")
    page.click('button[data-plan-schedule-mode="recurring"]')
    page.select_option("#planRecurrenceFrequency", "weekly")
    page.wait_for_function(
        "() => document.querySelector('#createPlanPreviewCard')?.textContent.includes('Еженедельно') && !document.querySelector('#createPlanPreviewCard')?.textContent.includes('Разовый')"
    )
    page.click('button[data-plan-weekday="0"]')
    page.click('button[data-plan-weekday="2"]')
    page.click('button[data-plan-weekday="4"]')
    page.click("#submitCreateOperationBtn")

    page.wait_for_selector("#createModal", state="hidden")
    page.wait_for_function("() => document.querySelector('#plansList')?.textContent.includes('Спортзал')")

    assert mock_state["last_create_payload"]["recurrence_enabled"] is True
    assert mock_state["last_create_payload"]["recurrence_frequency"] == "weekly"
    assert mock_state["last_create_payload"]["recurrence_weekdays"] == [0, 2, 4]
    assert mock_state["last_create_payload"]["recurrence_month_end"] is False
    assert page.locator("#plansList").text_content().find("Еженедельно: Пн, Ср, Пт") >= 0


@pytest.mark.e2e
def test_plans_ui_creates_month_end_plan_and_confirms_to_history(static_server_url: str, page_with_plans_api_mock):
    page, mock_state = page_with_plans_api_mock
    _login_and_open_plans(page, static_server_url)

    page.click("#addPlanCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.fill("#opDate", "2026-01-31")
    page.fill("#opAmount", "50")
    page.fill("#opNote", "Подписка")
    page.click('button[data-plan-schedule-mode="recurring"]')
    page.select_option("#planRecurrenceFrequency", "monthly")
    if not page.is_checked("#planRecurrenceMonthEnd"):
        page.check("#planRecurrenceMonthEnd")
    page.click("#submitCreateOperationBtn")

    page.wait_for_selector("#createModal", state="hidden")
    page.wait_for_function("() => document.querySelector('#plansList')?.textContent.includes('Подписка')")
    assert mock_state["last_create_payload"]["recurrence_month_end"] is True
    assert page.locator("#plansList").text_content().find("в последний день месяца") >= 0

    page.locator('#plansList button[data-plan-action="confirm"][data-plan-id="1"]').evaluate("(node) => node.click()")
    deadline = time.time() + 5
    while time.time() < deadline and not mock_state["history"]:
        time.sleep(0.1)

    assert len(mock_state["history"]) == 1
    assert mock_state["history"][0]["event_type"] == "confirmed"
    assert mock_state["history"][0]["effective_date"] == "2026-01-31"
    assert mock_state["plans"][0]["scheduled_date"] == "2026-02-28"

    page.click('button[data-plan-tab="history"]')
    page.wait_for_function("() => document.querySelector('#plansList')?.textContent.includes('Подтвержден')")
    history_text = page.locator("#plansList").text_content()
    assert "Подписка" in history_text
    assert "31.01.2026" in history_text


@pytest.mark.e2e
def test_plans_ui_creates_daily_workdays_plan(static_server_url: str, page_with_plans_api_mock):
    page, mock_state = page_with_plans_api_mock
    _login_and_open_plans(page, static_server_url)

    page.click("#addPlanCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.fill("#opDate", "2026-03-13")
    page.fill("#opAmount", "15")
    page.fill("#opNote", "Кофе в офисе")
    page.click('button[data-plan-schedule-mode="recurring"]')
    page.select_option("#planRecurrenceFrequency", "daily")
    page.check("#planRecurrenceWorkdaysOnly")
    page.click("#submitCreateOperationBtn")

    page.wait_for_selector("#createModal", state="hidden")
    page.wait_for_function("() => document.querySelector('#plansList')?.textContent.includes('Кофе в офисе')")

    assert mock_state["last_create_payload"]["recurrence_frequency"] == "daily"
    assert mock_state["last_create_payload"]["recurrence_workdays_only"] is True
    assert page.locator("#plansList").text_content().find("По будням") >= 0

    page.locator('#plansList button[data-plan-action="confirm"][data-plan-id="1"]').evaluate("(node) => node.click()")
    deadline = time.time() + 5
    while time.time() < deadline and not mock_state["history"]:
        time.sleep(0.1)

    assert len(mock_state["history"]) == 1
    assert mock_state["history"][0]["effective_date"] == "2026-03-13"
    assert mock_state["plans"][0]["scheduled_date"] == "2026-03-16"


@pytest.mark.e2e
def test_plans_history_event_type_filters(static_server_url: str, page_with_plans_api_mock):
    page, mock_state = page_with_plans_api_mock
    mock_state["history"][:] = [
        {
            "id": 3,
            "plan_id": 3,
            "operation_id": None,
            "event_type": "reminded",
            "kind": "expense",
            "amount": "9.00",
            "effective_date": "2026-03-18",
            "note": "Напомнить про кофе",
            "category_name": None,
            "created_at": "2026-03-18T09:00:00Z",
        },
        {
            "id": 2,
            "plan_id": 2,
            "operation_id": None,
            "event_type": "skipped",
            "kind": "expense",
            "amount": "40.00",
            "effective_date": "2026-03-17",
            "note": "Пропущенный платеж",
            "category_name": None,
            "created_at": "2026-03-17T09:00:00Z",
        },
        {
            "id": 1,
            "plan_id": 1,
            "operation_id": 101,
            "event_type": "confirmed",
            "kind": "expense",
            "amount": "15.00",
            "effective_date": "2026-03-16",
            "note": "Подтвержденный кофе",
            "category_name": None,
            "created_at": "2026-03-16T09:00:00Z",
        },
    ]
    _login_and_open_plans(page, static_server_url)

    page.click('button[data-plan-tab="history"]')
    page.wait_for_function("() => document.querySelector('#plansList')?.textContent.includes('Подтвержденный кофе')")
    history_text = page.locator("#plansList").text_content()
    assert "Подтвержденный кофе" in history_text
    assert "Пропущенный платеж" in history_text
    assert "Напомнить про кофе" in history_text

    page.click('button[data-plan-history-event="confirmed"]')
    page.wait_for_function(
        "() => { const text = document.querySelector('#plansList')?.textContent || ''; return text.includes('Подтвержденный кофе') && !text.includes('Пропущенный платеж') && !text.includes('Напомнить про кофе'); }"
    )
    page.click('button[data-plan-history-event="skipped"]')
    page.wait_for_function(
        "() => { const text = document.querySelector('#plansList')?.textContent || ''; return text.includes('Пропущенный платеж') && !text.includes('Подтвержденный кофе') && !text.includes('Напомнить про кофе'); }"
    )

    page.click('button[data-plan-history-event="reminded"]')
    page.wait_for_function(
        "() => { const text = document.querySelector('#plansList')?.textContent || ''; return text.includes('Напомнить про кофе') && !text.includes('Подтвержденный кофе') && !text.includes('Пропущенный платеж'); }"
    )
