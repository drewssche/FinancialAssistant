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
        "original_amount": plan.get("original_amount", plan["amount"]),
        "currency": plan.get("currency", "BYN"),
        "base_currency": plan.get("base_currency", "BYN"),
        "current_rate": plan.get("current_rate"),
        "current_rate_date": plan.get("current_rate_date"),
        "current_base_amount": plan.get("current_base_amount"),
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
        "debt_cards": [],
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
            include_closed = query.get("include_closed", ["false"])[0].lower() == "true"
            cards = list(mock_state["debt_cards"])
            if not include_closed:
                cards = [card for card in cards if card.get("status") == "active"]
            return _json_response(route, cards)
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
        if path.startswith("/api/v1/plans/") and path.count("/") == 4:
            plan_id = int(path.split("/")[-1])
            plan = next((item for item in mock_state["plans"] if int(item["id"]) == plan_id), None)
            if plan is None:
                return _json_response(route, {"detail": "Plan not found"}, status=404)
            if method == "PATCH":
                payload = json.loads(request.post_data or "{}")
                plan.update(
                    {
                        "kind": payload.get("kind", plan["kind"]),
                        "amount": payload.get("amount", plan["amount"]),
                        "scheduled_date": payload.get("scheduled_date", plan["scheduled_date"]),
                        "note": payload.get("note"),
                        "recurrence_enabled": bool(payload.get("recurrence_enabled")),
                        "recurrence_frequency": payload.get("recurrence_frequency"),
                        "recurrence_interval": int(payload.get("recurrence_interval") or 1),
                        "recurrence_weekdays": list(payload.get("recurrence_weekdays") or []),
                        "recurrence_workdays_only": bool(payload.get("recurrence_workdays_only")),
                        "recurrence_month_end": bool(payload.get("recurrence_month_end")),
                        "recurrence_end_date": payload.get("recurrence_end_date"),
                    }
                )
                return _json_response(route, _make_plan_item(plan))
            if method == "DELETE":
                mock_state["plans"][:] = [item for item in mock_state["plans"] if int(item["id"]) != plan_id]
                return _json_response(route, {"ok": True})
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
        if path.startswith("/api/v1/plans/") and path.endswith("/skip") and method == "POST":
            plan_id = int(path.split("/")[-2])
            plan = next(item for item in mock_state["plans"] if int(item["id"]) == plan_id)
            mock_state["history"].insert(
                0,
                {
                    "id": len(mock_state["history"]) + 1,
                    "plan_id": plan_id,
                    "operation_id": None,
                    "event_type": "skipped",
                    "kind": plan["kind"],
                    "amount": plan["amount"],
                    "effective_date": plan["scheduled_date"],
                    "note": plan.get("note"),
                    "category_name": None,
                    "created_at": "2026-03-16T12:05:00Z",
                },
            )
            plan["skip_count"] = int(plan.get("skip_count") or 0) + 1
            plan["last_skipped_at"] = "2026-03-16T12:05:00Z"
            plan["status"] = "skipped"
            return _json_response(route, _make_plan_item(plan))
        return _json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    _set_mock_telegram(page)
    page.route("**/api/v1/**", handler)
    return page, mock_state


def _login_and_open_plans(page, static_server_url: str):
    page.goto(f"{static_server_url}/static/index.html")
    _restore_mock_telegram(page)
    page.evaluate("() => window.App.getRuntimeModule('session')?.refreshTelegramLoginUi?.()")
    try:
        page.locator("#telegramLoginBtn").wait_for(state="visible", timeout=1200)
        page.click("#telegramLoginBtn")
        page.wait_for_selector("#appShell:not(.hidden)")
    except Exception:
        page.wait_for_selector("#appShell:not(.hidden)")
    page.click('button[data-section="plans"]')
    page.wait_for_selector("#plansSection:not(.hidden)")
    page.wait_for_selector("#addPlanCta:not(.hidden)")


def _login_and_open_dashboard(page, static_server_url: str):
    page.goto(f"{static_server_url}/static/index.html")
    _restore_mock_telegram(page)
    page.evaluate("() => window.App.getRuntimeModule('session')?.refreshTelegramLoginUi?.()")
    try:
      page.locator("#telegramLoginBtn").wait_for(state="visible", timeout=1200)
      page.click("#telegramLoginBtn")
      page.wait_for_selector("#appShell:not(.hidden)")
    except Exception:
      page.wait_for_selector("#appShell:not(.hidden)")
    page.wait_for_selector("#dashboardSection:not(.hidden)")
    page.wait_for_selector("#dashboardPlansPanel:not(.hidden)")


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
    if page.locator("#planRecurrenceMonthEnd").input_value() != "on":
        page.click('button[data-plan-month-end="on"]')
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
def test_plan_kebab_menu_actions_work_from_floating_popover(static_server_url: str, page_with_plans_api_mock):
    page, mock_state = page_with_plans_api_mock
    mock_state["plans"][:] = [
        {
            "id": 1,
            "kind": "expense",
            "amount": "15.00",
            "scheduled_date": "2026-03-20",
            "note": "Кебаб редактировать",
            "recurrence_enabled": True,
            "recurrence_frequency": "monthly",
            "recurrence_interval": 1,
            "recurrence_weekdays": [],
            "recurrence_workdays_only": False,
            "recurrence_month_end": False,
            "recurrence_end_date": None,
            "status": "upcoming",
            "confirm_count": 0,
            "skip_count": 0,
            "confirmed_operation_id": None,
            "created_at": "2026-03-16T12:00:00Z",
            "next_reminder_at": "2026-03-17T06:00:00Z",
        },
        {
            "id": 2,
            "kind": "expense",
            "amount": "20.00",
            "scheduled_date": "2026-03-21",
            "note": "Кебаб удалить",
            "recurrence_enabled": False,
            "recurrence_frequency": None,
            "recurrence_interval": 1,
            "recurrence_weekdays": [],
            "recurrence_workdays_only": False,
            "recurrence_month_end": False,
            "recurrence_end_date": None,
            "status": "upcoming",
            "confirm_count": 0,
            "skip_count": 0,
            "confirmed_operation_id": None,
            "created_at": "2026-03-16T12:00:00Z",
            "next_reminder_at": "2026-03-17T06:00:00Z",
        },
    ]
    _login_and_open_plans(page, static_server_url)
    page.wait_for_function("() => document.querySelector('#plansList')?.textContent.includes('Кебаб редактировать')")

    page.locator('button[data-plan-menu-trigger="1"]').click()
    page.locator('.plan-card-actions-popover:not(.hidden) button[data-plan-action="edit"][data-plan-id="1"]').click()
    page.wait_for_selector("#createModal:not(.hidden)")
    assert page.locator("#createTitle").text_content() == "Редактировать план"
    page.click("#closeCreateModalBtn")
    page.wait_for_selector("#createModal", state="hidden")

    page.locator('button[data-plan-menu-trigger="1"]').click()
    page.locator('.plan-card-actions-popover:not(.hidden) button[data-plan-action="skip"][data-plan-id="1"]').click()
    deadline = time.time() + 5
    while time.time() < deadline and mock_state["plans"][0]["status"] != "skipped":
        time.sleep(0.1)
    assert mock_state["plans"][0]["status"] == "skipped"
    page.wait_for_function("() => document.querySelector('#plansList')?.textContent.includes('Кебаб удалить')")

    page.locator('button[data-plan-menu-trigger="2"]').click()
    page.locator('.plan-card-actions-popover:not(.hidden) button[data-plan-action="delete"][data-plan-id="2"]').click()
    page.wait_for_selector("#confirmModal:not(.hidden)")
    page.click("#confirmDeleteBtn")
    page.wait_for_function("() => !(document.querySelector('#plansList')?.textContent || '').includes('Кебаб удалить')")
    assert [item["id"] for item in mock_state["plans"]] == [1]


@pytest.mark.e2e
def test_plan_foreign_currency_amount_meta_wraps_inside_card(static_server_url: str, page_with_plans_api_mock):
    page, mock_state = page_with_plans_api_mock
    mock_state["plans"][:] = [
        {
            "id": 1,
            "kind": "expense",
            "amount": "2178.74",
            "original_amount": "686.00",
            "currency": "EUR",
            "base_currency": "BYN",
            "current_rate": "3.17600",
            "current_rate_date": "2026-05-22",
            "current_base_amount": "2178.74",
            "scheduled_date": "2026-06-30",
            "status": "upcoming",
            "note": "За тур в Стамбул (остаток 762,5-76,5)",
            "created_at": "2026-05-22T12:00:00Z",
        }
    ]

    _login_and_open_plans(page, static_server_url)
    page.wait_for_function("() => document.querySelector('#plansList')?.textContent.includes('Стамбул')")
    geometry = page.locator("#plansList .plan-card").evaluate(
        """
        node => {
          const card = node.getBoundingClientRect();
          const amount = node.querySelector('.plan-card-amount').getBoundingClientRect();
          const secondary = node.querySelector('.plan-card-amount-secondary').getBoundingClientRect();
          return {
            cardLeft: card.left,
            cardRight: card.right,
            amountLeft: amount.left,
            amountRight: amount.right,
            secondaryLeft: secondary.left,
            secondaryRight: secondary.right,
          };
        }
        """
    )
    assert geometry["amountRight"] <= geometry["cardRight"] + 1
    assert geometry["secondaryRight"] <= geometry["cardRight"] + 1
    assert geometry["amountLeft"] >= geometry["cardLeft"] - 1
    assert geometry["secondaryLeft"] >= geometry["cardLeft"] - 1


@pytest.mark.e2e
def test_debt_counterparty_picker_loads_closed_counterparties_despite_active_debt_cache(static_server_url: str, page_with_plans_api_mock):
    page, mock_state = page_with_plans_api_mock
    mock_state["debt_cards"][:] = [
        {
            "counterparty": "Активный контакт",
            "counterparty_id": 1,
            "status": "active",
            "debts": [
                {
                    "id": 10,
                    "direction": "lend",
                    "principal": "100.00",
                    "currency": "BYN",
                    "start_date": "2026-03-01",
                    "due_date": None,
                    "note": "",
                    "outstanding_total": "100.00",
                }
            ],
        },
        {
            "counterparty": "Закрытый контакт",
            "counterparty_id": 2,
            "status": "closed",
            "debts": [
                {
                    "id": 11,
                    "direction": "lend",
                    "principal": "40.00",
                    "currency": "BYN",
                    "start_date": "2026-02-01",
                    "due_date": None,
                    "note": "",
                    "outstanding_total": "0.00",
                }
            ],
        },
    ]
    _login_and_open_plans(page, static_server_url)
    page.evaluate(
        """
        () => {
          window.App.state.debtCardsCache = [{
            counterparty: "Активный контакт",
            counterparty_id: 1,
            status: "active",
            debts: []
          }];
          window.App.state.debtCounterpartyCardsCache = null;
          window.App.state.debtCounterpartyCardsCacheLoaded = false;
        }
        """
    )
    page.evaluate("() => window.App.getRuntimeModule('operation-modal').openCreateModal({ entryMode: 'debt' })")
    page.wait_for_selector("#createModal:not(.hidden)")

    page.fill("#debtCounterparty", "Закр")
    page.wait_for_function("() => document.querySelector('#debtCounterpartyAll')?.textContent.includes('Закрытый контакт')")


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
    page.click('button[data-plan-workdays-only="on"]')
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


@pytest.mark.e2e
def test_dashboard_plans_period_tabs_switch_and_filter(static_server_url: str, page_with_plans_api_mock):
    page, mock_state = page_with_plans_api_mock
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    current_week_item = today + timedelta(days=1 if today.weekday() < 6 else 0)
    next_month_anchor = (today.replace(day=28) + timedelta(days=4)).replace(day=5)
    overdue_item = today - timedelta(days=3)
    mock_state["plans"][:] = [
        {
            "id": 1,
            "kind": "expense",
            "amount": "11.00",
            "scheduled_date": overdue_item.isoformat(),
            "note": "Просроченный план",
            "recurrence_enabled": False,
            "recurrence_frequency": None,
            "recurrence_interval": 1,
            "recurrence_weekdays": [],
            "recurrence_workdays_only": False,
            "recurrence_month_end": False,
            "recurrence_end_date": None,
            "status": "overdue",
            "confirm_count": 0,
            "skip_count": 0,
            "confirmed_operation_id": None,
            "created_at": f"{start_of_week.isoformat()}T09:00:00Z",
            "next_reminder_at": f"{today.isoformat()}T06:00:00Z",
        },
        {
            "id": 2,
            "kind": "expense",
            "amount": "22.00",
            "scheduled_date": current_week_item.isoformat(),
            "note": "План недели",
            "recurrence_enabled": False,
            "recurrence_frequency": None,
            "recurrence_interval": 1,
            "recurrence_weekdays": [],
            "recurrence_workdays_only": False,
            "recurrence_month_end": False,
            "recurrence_end_date": None,
            "status": "upcoming",
            "confirm_count": 0,
            "skip_count": 0,
            "confirmed_operation_id": None,
            "created_at": f"{today.isoformat()}T09:00:00Z",
            "next_reminder_at": f"{today.isoformat()}T09:00:00Z",
        },
        {
            "id": 3,
            "kind": "income",
            "amount": "33.00",
            "scheduled_date": next_month_anchor.isoformat(),
            "note": "План всех времен",
            "recurrence_enabled": False,
            "recurrence_frequency": None,
            "recurrence_interval": 1,
            "recurrence_weekdays": [],
            "recurrence_workdays_only": False,
            "recurrence_month_end": False,
            "recurrence_end_date": None,
            "status": "upcoming",
            "confirm_count": 0,
            "skip_count": 0,
            "confirmed_operation_id": None,
            "created_at": f"{today.isoformat()}T12:00:00Z",
            "next_reminder_at": f"{today.isoformat()}T09:00:00Z",
        },
    ]

    _login_and_open_dashboard(page, static_server_url)

    page.wait_for_function(
        "() => { const text = document.querySelector('#dashboardPlansList')?.textContent || ''; return text.includes('Просроченный план') && text.includes('План недели') && !text.includes('План всех времен'); }"
    )
    assert "Планы на месяц:" in (page.locator("#dashboardPlansPeriodLabel").text_content() or "")

    page.click('button[data-dashboard-plans-period="all_time"]')
    page.wait_for_function(
        "() => { const text = document.querySelector('#dashboardPlansList')?.textContent || ''; return text.includes('План всех времен'); }"
    )
    assert "Все активные планы" in (page.locator("#dashboardPlansPeriodLabel").text_content() or "")

    page.click('button[data-dashboard-plans-period="week"]')
    page.wait_for_function(
        "() => { const text = document.querySelector('#dashboardPlansList')?.textContent || ''; return text.includes('Просроченный план') && text.includes('План недели') && !text.includes('План всех времен'); }"
    )
    assert "Планы на неделю:" in (page.locator("#dashboardPlansPeriodLabel").text_content() or "")


@pytest.mark.e2e
def test_work_timesheet_renders_auto_days_payroll_shift_and_plan_links(static_server_url: str, page_with_plans_api_mock):
    page, mock_state = page_with_plans_api_mock
    page.add_init_script(
        """
        (() => {
          const NativeDate = Date;
          const fixedNow = new NativeDate('2026-08-10T11:30:00+03:00').valueOf();
          class FixedDate extends NativeDate {
            constructor(...args) { super(...(args.length ? args : [fixedNow])); }
            static now() { return fixedNow; }
          }
          window.Date = FixedDate;
        })();
        """
    )
    mock_state["plans"] = [
        {
            "id": 3,
            "kind": "income",
            "amount": "1050.00",
            "scheduled_date": "2026-08-20",
            "note": "Аванс",
            "recurrence_enabled": True,
            "recurrence_frequency": "monthly",
            "recurrence_interval": 1,
        },
        {
            "id": 4,
            "kind": "income",
            "amount": "1176.00",
            "scheduled_date": "2026-09-04",
            "note": "Основная часть",
            "recurrence_enabled": True,
            "recurrence_frequency": "monthly",
            "recurrence_interval": 1,
        },
    ]

    days = []
    for day_number in range(1, 32):
        current = date(2026, 8, day_number)
        is_workday = current.weekday() < 5
        days.append(
            {
                "date": current.isoformat(),
                "weekday": current.weekday(),
                "status": "workday" if is_workday else "weekend",
                "status_label": "Рабочий день" if is_workday else "Выходной",
                "calendar_label": "Рабочий день" if is_workday else "Выходной",
                "planned_hours": "8.00" if is_workday else "0.00",
                "actual_hours": "2.50" if day_number == 10 else ("8.00" if is_workday and day_number <= 9 else "0.00"),
                "credited_hours": "2.50" if day_number == 10 else ("8.00" if is_workday and day_number <= 9 else "0.00"),
                "is_workday": is_workday,
                "is_manual": False,
                "is_future": day_number > 10,
                "is_live": day_number == 10,
                "is_completed": is_workday and day_number <= 9,
                "hours_state": "live" if day_number == 10 else ("forecast" if day_number > 10 else "actual"),
                "note": None,
            }
        )
    days[2]["note"] = "Встреча с командой"
    days[2]["is_manual"] = True

    contracts_payload = [
        {
            "id": 12,
            "effective_from": "2024-04-29",
            "effective_to": None,
            "company": "Битрикс",
            "position": None,
            "salary_amount": "3200.00",
            "currency": "BYN",
            "note": None,
            "created_at": "2024-04-29T09:00:00Z",
        }
    ]
    companies_payload = [
        {
            "company": "Битрикс",
            "effective_from": "2024-04-29",
            "effective_to": None,
            "is_current": True,
            "contract_count": 1,
            "salary_operation_count": 12,
            "positions": ["Разработчик"],
            "earnings": [{"currency": "BYN", "amount": "18450.00"}],
            "periods": [
                {
                    "id": 12,
                    "effective_from": "2024-04-29",
                    "effective_to": None,
                    "position": "Разработчик",
                    "salary_amount": "3200.00",
                    "currency": "BYN",
                    "note": None,
                }
            ],
        }
    ]
    updated_contracts = []
    actual_salary = {
        "role": "salary",
        "label": "Основная часть",
        # Историческая выплата должна оставаться видимой после смены текущего плана.
        "plan_id": 44,
        "link_id": 900,
        "operation_id": 701,
        "source_operation_id": 701,
        "operation_date": "2026-08-07",
        "amount": "1234.56",
        "currency": "BYN",
        "base_amount": "1234.56",
        "base_currency": "BYN",
        "note": "Зарплата за июль",
        "category_name": "Зарплата",
        "is_deleted": False,
        "source": "plan_confirmation",
    }
    detected_salary = {
        "label": "Зарплата",
        "link_id": None,
        "operation_id": 703,
        "source_operation_id": 703,
        "operation_date": "2026-08-05",
        "amount": "1973.56",
        "currency": "BYN",
        "base_amount": "1973.56",
        "base_currency": "BYN",
        "note": "Отпускные и премия",
        "category_name": "Зарплата",
        "is_deleted": False,
        "source": "category_match",
    }
    manual_candidate = {
        "operation_id": 702,
        "operation_date": "2026-08-08",
        "amount": "850.00",
        "currency": "BYN",
        "base_amount": "850.00",
        "base_currency": "BYN",
        "note": "Аванс, добавленный вручную",
        "category_name": "Зарплата",
        "is_linked": False,
        "link_id": None,
        "linked_role": None,
    }
    payment_history_items = [actual_salary]
    payment_link_requests = []
    payment_unlink_requests = []
    work_month_requests = []

    month_payload = {
        "year": 2026,
        "month": 8,
        "profile": {
            "id": 1,
            "company": "Битрикс",
            "position": "Разработчик",
            "employment_start_date": "2024-04-29",
            "standard_hours_per_day": "8.00",
            "workday_start_time": "09:00:00",
            "workday_end_time": "18:00:00",
            "lunch_start_time": "13:00:00",
            "lunch_end_time": "14:00:00",
            "workweek_days": [0, 1, 2, 3, 4],
            "country_code": "BY",
            "advance_plan_id": 3,
            "salary_plan_id": 4,
            "advance_nominal_day": 20,
            "salary_nominal_day": 5,
            "payment_shift_rule": "previous_workday",
        },
        "summary": {
            "planned_days": 21,
            "completed_days": 5,
            "planned_hours": "168.00",
            "actual_hours": "40.00",
            "credited_hours": "40.00",
            "vacation_days": 0,
            "sick_days": 0,
            "override_days": 0,
        },
        "payments": [
            {
                "role": "salary",
                "label": "Основная часть",
                "plan_id": 4,
                "nominal_date": "2026-08-05",
                "effective_date": "2026-08-05",
                "shifted": False,
                "forecast_visible": False,
                "forecast_amount": None,
                "forecast_currency": None,
                "forecast_base_amount": None,
                "forecast_base_currency": None,
                "actual_operations": [
                    {key: value for key, value in actual_salary.items() if key not in {"role", "label", "plan_id"}}
                ],
            },
            {
                "role": "advance",
                "label": "Аванс",
                "plan_id": 3,
                "nominal_date": "2026-08-20",
                "effective_date": "2026-08-20",
                "shifted": False,
                "forecast_visible": True,
                "forecast_amount": "1050.00",
                "forecast_currency": "BYN",
                "forecast_base_amount": "1050.00",
                "forecast_base_currency": "BYN",
                "actual_operations": [],
            },
        ],
        "payroll_operations": [detected_salary],
        "days": days,
    }
    statistics_payload = {
        "period": "month",
        "date_from": "2026-08-01",
        "date_to": "2026-08-31",
        "calendar_days": 31,
        "planned_days": 21,
        "completed_days": 5,
        "planned_hours": "168.00",
        "actual_hours": "40.00",
        "credited_hours": "40.00",
        "future_planned_hours": "128.00",
        "completion_percent": "23.81",
        "vacation_days": 0,
        "sick_days": 0,
        "overtime_hours": "0.00",
        "override_days": 0,
        "months": [{
            "month": "2026-08",
            "planned_days": 21,
            "completed_days": 5,
            "planned_hours": "168.00",
            "actual_hours": "40.00",
            "credited_hours": "40.00",
            "override_days": 0,
        }],
    }

    def work_handler(route, request):
        path = urlparse(request.url).path
        method = request.method.upper()
        if path == "/api/v1/work/month":
            work_month_requests.append(request.url)
            return _json_response(route, month_payload)
        if path == "/api/v1/work/payments/history" and method == "GET":
            return _json_response(route, {"items": payment_history_items, "total": len(payment_history_items)})
        if path == "/api/v1/work/payments/candidates" and method == "GET":
            return _json_response(route, {"items": [manual_candidate], "total": 1})
        if path == "/api/v1/work/payments/links" and method == "POST":
            payload = json.loads(request.post_data or "{}")
            payment_link_requests.append(payload)
            manual_candidate.update({"is_linked": True, "link_id": 901, "linked_role": payload["role"]})
            linked_item = {
                "role": payload["role"],
                "label": "Аванс" if payload["role"] == "advance" else "Основная часть",
                "plan_id": None,
                **{
                    key: value
                    for key, value in manual_candidate.items()
                    if key not in {"is_linked", "linked_role"}
                },
                "source": "manual",
                "source_operation_id": manual_candidate["operation_id"],
                "is_deleted": False,
            }
            payment_history_items.append(linked_item)
            return _json_response(route, linked_item, status=201)
        if path == "/api/v1/work/payments/links/901" and method == "DELETE":
            payment_unlink_requests.append(901)
            payment_history_items[:] = [item for item in payment_history_items if item.get("link_id") != 901]
            manual_candidate.update({"is_linked": False, "link_id": None, "linked_role": None})
            return route.fulfill(status=204, body="")
        if path == "/api/v1/work/statistics":
            return _json_response(route, statistics_payload)
        if path == "/api/v1/work/companies" and method == "GET":
            return _json_response(route, companies_payload)
        if path == "/api/v1/work/contracts" and method == "GET":
            return _json_response(route, contracts_payload)
        if path == "/api/v1/work/contracts/12" and method == "PUT":
            payload = json.loads(request.post_data or "{}")
            contracts_payload[0].update(payload)
            updated_contracts.append(payload)
            return _json_response(route, contracts_payload[0])
        return _json_response(route, {"detail": f"Unhandled work route: {request.method} {path}"}, status=404)

    page.route("**/api/v1/work/**", work_handler)
    page.route(
        "**/api/v1/operations/701",
        lambda route: _json_response(
            route,
            {
                "id": 701,
                "kind": "income",
                "amount": "1234.56",
                "original_amount": "1234.56",
                "currency": "BYN",
                "base_currency": "BYN",
                "fx_rate": "1.000000",
                "operation_date": "2026-08-07",
                "category_id": None,
                "category_name": "Зарплата",
                "category_icon": None,
                "category_accent_color": None,
                "note": "Зарплата за июль",
                "receipt_items": [],
                "receipt_total": None,
                "receipt_discrepancy": None,
                "fx_settlement": None,
            },
        ),
    )
    page.route(
        "**/api/v1/operations/702",
        lambda route: _json_response(
            route,
            {
                "id": 702,
                "kind": "income",
                "amount": "850.00",
                "original_amount": "850.00",
                "currency": "BYN",
                "base_currency": "BYN",
                "fx_rate": "1.000000",
                "operation_date": "2026-08-08",
                "category_id": None,
                "category_name": "Зарплата",
                "category_icon": None,
                "category_accent_color": None,
                "note": "Аванс, добавленный вручную",
                "receipt_items": [],
                "receipt_total": None,
                "receipt_discrepancy": None,
                "fx_settlement": None,
            },
        ),
    )
    page.route(
        "**/api/v1/operations/703",
        lambda route: _json_response(
            route,
            {
                "id": 703,
                "kind": "income",
                "amount": "1973.56",
                "original_amount": "1973.56",
                "currency": "BYN",
                "base_currency": "BYN",
                "fx_rate": "1.000000",
                "operation_date": "2026-08-05",
                "category_id": 45,
                "category_name": "Зарплата",
                "category_icon": None,
                "category_accent_color": None,
                "note": "Отпускные и премия",
                "receipt_items": [],
                "receipt_total": None,
                "receipt_discrepancy": None,
                "fx_settlement": None,
            },
        ),
    )
    _login_and_open_dashboard(page, static_server_url)
    page.click('button[data-section="work"]')
    page.wait_for_selector("#workSection:not(.hidden)")
    page.wait_for_selector("#workStatisticsView:not(.hidden)")
    assert "168 ч" in (page.locator("#workStatisticsKpi").text_content() or "")
    assert "Август 2026" in (page.locator("#workMonthTrigger").text_content() or "")
    page.click("#workMonthTrigger")
    page.wait_for_selector("#workMonthPopover:not(.hidden)")
    page.click('[data-work-picker-year="2024"]')
    page.click('[data-work-picker-month="2024-05"]')
    page.wait_for_function("() => document.querySelector('#workMonthTrigger')?.textContent?.includes('Май 2024')")
    page.click("#workTodayBtn")

    page.click('button[data-work-view="timesheet"]')
    page.wait_for_selector('#workCalendarGrid [data-work-date="2026-08-03"]')

    assert page.locator("#workCalendarGrid .work-day-cell").count() == 36
    assert "168 ч" in (page.locator("#workSummaryGrid").text_content() or "")
    assert "Аванс" in (page.locator("#workPaymentsGrid").text_content() or "")
    assert "Факт · 1 234,56" in (page.locator("#workPaymentsGrid").text_content() or "").replace("\u00a0", " ")
    assert "Получено · 1 234,56" in (page.locator("#workPaymentsGrid").text_content() or "").replace("\u00a0", " ")
    assert "is-completed" in (page.locator('[data-work-date="2026-08-03"]').get_attribute("class") or "")
    assert "is-forecast" in (page.locator('[data-work-date="2026-08-11"]').get_attribute("class") or "")
    assert "is-today" in (page.locator('[data-work-date="2026-08-10"]').get_attribute("class") or "")
    assert "Сегодня" in (page.locator('[data-work-date="2026-08-10"]').text_content() or "")
    assert "Факт · 8 ч" in (page.locator('[data-work-date="2026-08-03"] .work-hours-chip-fact').text_content() or "")
    assert "Сейчас · 2 ч 30 мин" in (page.locator('[data-work-date="2026-08-10"] .work-hours-chip-live').text_content() or "")
    assert "План · 8 ч" in (page.locator('[data-work-date="2026-08-10"] .work-hours-chip-plan').text_content() or "")
    assert "Прогноз · 8 ч" in (page.locator('[data-work-date="2026-08-11"] .work-hours-chip-forecast').text_content() or "")
    assert "Встреча с командой" in (page.locator('[data-work-date="2026-08-03"] .work-day-note').text_content() or "")
    assert page.locator('[data-work-date="2026-08-05"] .work-day-payment-forecast').count() == 0
    detected_chip = page.locator('[data-work-date="2026-08-05"] .work-day-payment-actual')
    detected_chip_text = (detected_chip.text_content() or "").replace("\u00a0", " ")
    assert "Зарплата · получено 1 973,56" in detected_chip_text
    assert "Отпускные и премия" in detected_chip_text
    assert "Определено по категории · Отпускные и премия" in (detected_chip.get_attribute("title") or "")
    assert "Основная часть · получено 1 234,56" in (page.locator('[data-work-date="2026-08-07"] .work-day-payment-actual').text_content() or "").replace("\u00a0", " ")
    assert "Аванс · прогноз · 1 050" in (page.locator('[data-work-date="2026-08-20"] .work-day-payment-forecast').text_content() or "").replace("\u00a0", " ")

    detected_chip.click()
    page.wait_for_selector("#editModal:not(.hidden)")
    assert page.locator("#editAmount").input_value() == "1973.56"
    page.click("#closeEditModalBtn")

    month_payload["payments"][1]["forecast_amount"] = "1100.00"
    month_payload["payments"][1]["forecast_base_amount"] = "1100.00"
    previous_month_request_count = len(work_month_requests)
    page.evaluate(
        """document.dispatchEvent(new CustomEvent("app:activity-changed", { detail: { method: "PATCH", path: "/api/v1/plans/3" } }))"""
    )
    page.wait_for_function(
        """() => (document.querySelector('[data-work-date="2026-08-20"] .work-day-payment-forecast')?.textContent || '').replace(/\u00a0/g, ' ').includes('1 100')"""
    )
    assert len(work_month_requests) > previous_month_request_count

    previous_month_request_count = len(work_month_requests)
    with page.expect_response(
        lambda response: urlparse(response.url).path == "/api/v1/work/month"
    ):
        page.evaluate(
            """document.dispatchEvent(new CustomEvent("app:activity-changed", { detail: { method: "POST", path: "/api/v1/operations" } }))"""
        )
    assert len(work_month_requests) > previous_month_request_count

    page.click('[data-work-date="2026-08-07"] .work-day-payment-actual')
    page.wait_for_selector("#editModal:not(.hidden)")
    assert page.locator("#editAmount").input_value() == "1234.56"
    page.click("#closeEditModalBtn")

    page.click('#workCalendarGrid [data-work-date="2026-08-03"]')
    page.wait_for_selector("#workDayForm:not(.hidden)")
    assert page.locator("#workDayStatus").input_value() == "workday"
    assert page.locator('[data-date-picker-trigger="workDayDateTo"]').count() == 1

    page.click('[data-work-open-plan-picker="salary"]')
    page.wait_for_selector("#workSettingsForm:not(.hidden)")
    assert page.locator("#workSalaryPlan").input_value() == "4"
    assert page.locator("#workAdvancePlan").input_value() == "3"
    assert page.locator("#workDayStartTime").input_value() == "09:00:00"
    assert page.locator("#workLunchEndTime").input_value() == "14:00:00"

    page.click('button[data-work-view="companies"]')
    company_grid_text = (page.locator("#workCompaniesGrid").text_content() or "").replace("\u00a0", " ")
    assert "18 450 BYN" in company_grid_text
    assert "Разработчик" in (page.locator("#workCompanyDetails").text_content() or "")
    assert page.locator('#workCompanyOptions option[value="Битрикс"]').count() == 1

    page.click('button[data-work-view="contracts"]')
    actual_payment_text = (page.locator("#workActualPaymentsList").text_content() or "").replace("\u00a0", " ")
    assert "Основная часть" in actual_payment_text
    assert "1 234,56" in actual_payment_text
    assert "Операция #701" in actual_payment_text
    page.click("#workPaymentLinkToggle")
    page.wait_for_selector("#workPaymentLinkPanel:not(.hidden)")
    assert page.locator("#workPaymentCandidateDateFrom").input_value() == "2026-08-01"
    assert page.locator("#workPaymentCandidateDateTo").input_value() == "2026-08-31"
    assert "Аванс, добавленный вручную" in (page.locator("#workPaymentCandidatesList").text_content() or "")
    page.click('[data-work-payment-link-role="advance"]')
    page.click('[data-work-link-operation="702"]')
    page.wait_for_function("() => document.querySelector('#workActualPaymentsList')?.textContent?.includes('Операция #702')")
    assert payment_link_requests[-1] == {"operation_id": 702, "role": "advance"}
    linked_text = (page.locator("#workActualPaymentsList").text_content() or "").replace("\u00a0", " ")
    assert "Связано вручную" in linked_text
    assert "850" in linked_text
    assert "Аванс · получено 850" in (page.locator('[data-work-date="2026-08-08"] .work-day-payment-actual').text_content() or "").replace("\u00a0", " ")

    page.click('#workActualPaymentsList [data-work-operation-id="702"]')
    page.wait_for_selector("#editModal:not(.hidden)")
    assert page.locator("#editAmount").input_value() == "850.00"
    page.click("#closeEditModalBtn")
    page.click('[data-work-unlink-payment="901"]')
    page.wait_for_selector("#confirmModal:not(.hidden)")
    assert page.locator("#confirmDeleteBtn").inner_text() == "Отвязать"
    page.click("#confirmDeleteBtn")
    page.wait_for_function("() => !document.querySelector('#workActualPaymentsList')?.textContent?.includes('Операция #702')")
    assert payment_unlink_requests == [901]
    page.wait_for_selector('[data-work-link-operation="702"]')

    page.click('[data-edit-work-contract="12"]')
    assert page.locator("#workContractPosition").input_value() == ""
    assert page.locator("#workContractCompany").input_value() == "Битрикс"
    assert page.locator("#workContractSubmitBtn").text_content() == "Сохранить изменения"
    page.locator("#workContractPosition").fill("Ведущий разработчик")
    page.click("#workContractSubmitBtn")
    page.wait_for_function("() => document.querySelector('#workContractsList')?.textContent?.includes('Ведущий разработчик')")
    assert updated_contracts[-1]["position"] == "Ведущий разработчик"
