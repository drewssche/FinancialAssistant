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


def _login_via_mock_telegram(page):
    _restore_mock_telegram(page)
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")
    try:
        page.locator("#telegramLoginBtn").wait_for(state="visible", timeout=1200)
        page.click("#telegramLoginBtn")
        page.wait_for_selector("#appShell:not(.hidden)")
    except Exception:
        page.wait_for_selector("#appShell:not(.hidden)")


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


def _item_templates_payload():
    items: list[dict] = []
    for idx in range(1, 10):
        items.append(
            {
                "id": idx,
                "shop_name": "Cofix" if idx <= 5 else "Prowine",
                "name": f"Позиция {idx}",
                "use_count": 10 + idx,
                "latest_unit_price": f"{5 + idx / 10:.2f}",
                "last_used_at": f"2026-03-{10 + idx:02d}T12:00:00Z",
                "category_name": "Кофе" if idx <= 5 else "Напитки",
                "category_icon": "☕" if idx <= 5 else "🍷",
                "category_accent_color": "#d9b86b" if idx <= 5 else "#c76f61",
            }
        )
    return {"items": items, "total": len(items), "page": 1, "page_size": 50}


def _categories_payload():
    return {
        "items": [
            {"id": 1, "name": "Алкоголь", "kind": "expense", "group_id": 101, "icon": "🍺"},
            {"id": 2, "name": "Сигареты", "kind": "expense", "group_id": 101, "icon": "🚬"},
            {"id": 3, "name": "Зарплата", "kind": "income", "group_id": 201, "icon": "💵"},
        ],
        "total": 3,
        "page": 1,
        "page_size": 20,
    }


def _category_groups_payload():
    return [
        {"id": 101, "name": "Вредные продукты", "kind": "expense", "accent_color": "#ff8a7a"},
        {"id": 201, "name": "Доходы", "kind": "income", "accent_color": "#4fd47d"},
    ]


def _debt_cards_payload():
    return [
        {
            "id": 1,
            "counterparty": "Надя",
            "status": "active",
            "created_at": "2026-03-11T09:00:00Z",
            "debts": [
                {
                    "id": 11,
                    "direction": "borrow",
                    "principal": "508.39",
                    "outstanding_total": "158.39",
                    "repaid_total": "350.00",
                    "due_date": None,
                    "created_at": "2025-09-22T12:00:00Z",
                }
            ],
        }
    ]


def _operations_payload():
    return {
        "items": [
            {
                "id": 1,
                "kind": "expense",
                "amount": "20.00",
                "operation_date": "2026-03-18",
                "category_id": 1,
                "category_name": "Игры/софт/курсы",
                "category_icon": "🎮",
                "category_accent_color": "#8f6bd1",
                "note": "STAR WARS Jedi Bundle",
                "receipt_items": [],
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }


def _build_handler(active_section: str):
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
            "plans": {"status_filter": "all", "reminders_enabled": True},
            "ui": {"active_section": active_section, "timezone": "Europe/Moscow"},
        },
    }
    item_templates = _item_templates_payload()
    categories = _categories_payload()
    category_groups = _category_groups_payload()
    debt_cards = _debt_cards_payload()
    operations = _operations_payload()

    def handler(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        query = parse_qs(parsed.query)
        method = request.method.upper()

        if path == "/api/v1/auth/public-config":
            return _json_response(route, {"telegram_bot_username": None, "browser_login_available": False})
        if path == "/api/v1/auth/telegram" and method == "POST":
            return _json_response(route, {"access_token": "mobile-shell-token", "token_type": "bearer"})
        if path == "/api/v1/users/me" and method == "GET":
            return _json_response(
                route,
                {
                    "id": 1,
                    "display_name": "Mobile Shell",
                    "username": "mobile_shell",
                    "telegram_id": "771100",
                    "status": "approved",
                    "is_admin": False,
                },
            )
        if path == "/api/v1/preferences":
            if method == "GET":
                return _json_response(route, preferences)
            if method == "PUT":
                payload = json.loads(request.post_data or "{}")
                preferences["preferences_version"] = payload.get("preferences_version", preferences["preferences_version"])
                preferences["data"] = payload.get("data", preferences["data"])
                return _json_response(route, preferences)
        if path == "/api/v1/categories/groups" and method == "GET":
            return _json_response(route, category_groups)
        if path == "/api/v1/categories" and method == "GET":
            if "page" in query and "page_size" in query:
                return _json_response(route, categories)
            return _json_response(route, categories["items"])
        if path == "/api/v1/operations/item-templates" and method == "GET":
            return _json_response(route, item_templates)
        if path.startswith("/api/v1/operations/item-templates/") and path.endswith("/prices") and method == "GET":
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
            return _json_response(route, {"month": "2026-03", "weeks": [], "days": [], "income_total": "0.00", "expense_total": "0.00", "balance": "0.00", "operations_count": 0})
        if path == "/api/v1/operations" and method == "GET":
            return _json_response(route, operations)
        if path == "/api/v1/debts/cards" and method == "GET":
            return _json_response(route, debt_cards)
        if path == "/api/v1/plans" and method == "GET":
            return _json_response(route, [])
        if path == "/api/v1/plans/history" and method == "GET":
            return _json_response(route, [])
        return _json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    return handler


@pytest.mark.e2e
def test_mobile_nav_toggle_stays_square_and_sticky(static_server_url: str):
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page(viewport={"width": 430, "height": 932})
        _set_mock_telegram(page)
        page.route("**/api/v1/**", _build_handler("item_catalog"))
        try:
            page.goto(f"{static_server_url}/static/index.html")
            _login_via_mock_telegram(page)
            button = page.locator("#mobileNavToggleBtn")
            button.wait_for(state="visible")
            first_rect = button.evaluate(
                "node => { const r = node.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height, position: getComputedStyle(node).position }; }"
            )
            assert first_rect["position"] == "fixed"
            assert abs(first_rect["width"] - first_rect["height"]) <= 1.5
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(200)
            second_rect = button.evaluate(
                "node => { const r = node.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height, position: getComputedStyle(node).position }; }"
            )
            assert second_rect["position"] == "fixed"
            assert abs(second_rect["width"] - second_rect["height"]) <= 1.5
            assert abs(second_rect["y"] - first_rect["y"]) <= 6
        finally:
            browser.close()


@pytest.mark.e2e
def test_mobile_card_kebab_stays_top_right_and_menu_escapes_card(static_server_url: str):
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page(viewport={"width": 430, "height": 932})
        _set_mock_telegram(page)
        page.route("**/api/v1/**", _build_handler("categories"))
        try:
            page.goto(f"{static_server_url}/static/index.html")
            _login_via_mock_telegram(page)

            category_card = page.locator(".category-mobile-group-card").first
            category_trigger = page.locator(".category-mobile-group-card .mobile-card-kebab-trigger").first
            category_trigger.wait_for(state="visible")
            card_box = category_card.bounding_box()
            trigger_box = category_trigger.bounding_box()
            assert card_box is not None and trigger_box is not None
            assert (card_box["x"] + card_box["width"]) - (trigger_box["x"] + trigger_box["width"]) <= 28
            category_trigger.click()
            category_menu = page.locator(".category-mobile-group-card .mobile-card-actions-popover:not(.hidden)").first
            category_menu.wait_for(state="visible")
            menu_box = category_menu.bounding_box()
            assert menu_box is not None
            assert menu_box["y"] + menu_box["height"] > card_box["y"] + card_box["height"] + 8
            assert page.locator(".category-mobile-group-row").first.evaluate("node => getComputedStyle(node).overflow") == "visible"
            assert page.locator(".category-mobile-group-cell").first.evaluate("node => getComputedStyle(node).overflow") == "visible"

            page.locator("#mobileNavToggleBtn").evaluate("node => node.click()")
            page.locator("button[data-section='item_catalog']").click()
            item_card = page.locator(".item-catalog-mobile-group-card").first
            item_trigger = page.locator(".item-catalog-mobile-group-card .mobile-card-kebab-trigger").first
            item_trigger.wait_for(state="visible")
            item_card_box = item_card.bounding_box()
            item_trigger_box = item_trigger.bounding_box()
            assert item_card_box is not None and item_trigger_box is not None
            assert (item_card_box["x"] + item_card_box["width"]) - (item_trigger_box["x"] + item_trigger_box["width"]) <= 28
            item_trigger.click()
            item_menu = page.locator(".item-catalog-mobile-group-card .mobile-card-actions-popover:not(.hidden)").first
            item_menu.wait_for(state="visible")
            item_menu_box = item_menu.bounding_box()
            assert item_menu_box is not None
            assert item_menu_box["y"] + item_menu_box["height"] > item_card_box["y"] + item_card_box["height"] + 8
            assert page.locator(".item-catalog-mobile-group-row").first.evaluate("node => getComputedStyle(node).overflow") == "visible"
            assert page.locator(".item-catalog-mobile-group-cell").first.evaluate("node => getComputedStyle(node).overflow") == "visible"
            page.mouse.click(20, 20)
            page.wait_for_timeout(100)
            assert "mobile-card-menu-open" not in (page.locator(".item-catalog-mobile-group-card").first.get_attribute("class") or "")

            page.locator("#mobileNavToggleBtn").evaluate("node => node.click()")
            page.locator("button[data-section='operations']").click()
            operation_card = page.locator(".mobile-card-table.operations-table tr[data-operation-row-id]").first
            operation_trigger = page.locator(".mobile-card-table.operations-table td.mobile-actions-cell .table-kebab-trigger").first
            operation_trigger.wait_for(state="visible")
            operation_card_box = operation_card.bounding_box()
            operation_trigger_box = operation_trigger.bounding_box()
            assert operation_card_box is not None and operation_trigger_box is not None
            assert (operation_card_box["x"] + operation_card_box["width"]) - (operation_trigger_box["x"] + operation_trigger_box["width"]) <= 28

            page.locator("#mobileNavToggleBtn").evaluate("node => node.click()")
            page.locator("button[data-section='debts']").click()
            debt_card = page.locator(".debt-mobile-entry").first
            debt_trigger = page.locator(".debt-mobile-entry .mobile-card-kebab-trigger").first
            debt_trigger.wait_for(state="visible")
            debt_card_box = debt_card.bounding_box()
            debt_trigger_box = debt_trigger.bounding_box()
            assert debt_card_box is not None and debt_trigger_box is not None
            assert (debt_card_box["x"] + debt_card_box["width"]) - (debt_trigger_box["x"] + debt_trigger_box["width"]) <= 28
            debt_trigger.click()
            debt_menu = page.locator(".debt-mobile-entry .mobile-card-actions-popover:not(.hidden)").first
            debt_menu.wait_for(state="visible")
            debt_menu_box = debt_menu.bounding_box()
            assert debt_menu_box is not None
            assert debt_menu_box["x"] >= debt_card_box["x"]
            assert debt_menu_box["y"] >= debt_trigger_box["y"] - 8
            assert page.locator(".debt-mobile-entry").first.evaluate("node => getComputedStyle(node).overflow") == "visible"
        finally:
            browser.close()
