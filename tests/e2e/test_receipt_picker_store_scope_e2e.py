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
def page_with_receipt_api_mock():
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"filters": {"kind": "", "q": ""}},
            "ui": {"active_section": "dashboard", "timezone": "Europe/Moscow"},
        },
    }

    categories = [
        {
            "id": 101,
            "name": "Еда",
            "icon": "🍔",
            "kind": "expense",
            "group_id": None,
            "group_name": None,
            "group_icon": None,
            "group_accent_color": None,
            "is_system": False,
        },
    ]

    templates = [
        {
            "id": 1,
            "shop_name": "Соседи",
            "name": "Ротманс",
            "latest_unit_price": "6.60",
        },
        {
            "id": 2,
            "shop_name": "Евроопт",
            "name": "Хлеб",
            "latest_unit_price": "2.20",
        },
    ]

    def json_response(route, payload: dict | list, status: int = 200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def handler(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        query = parse_qs(parsed.query)
        method = request.method.upper()

        if path == "/api/v1/auth/dev" and method == "POST":
            return json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})
        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "Receipt User", "username": "receipt_user"})
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
                return json_response(route, {"items": categories, "total": len(categories), "page": 1, "page_size": 20})
            return json_response(route, categories)
        if path == "/api/v1/dashboard/summary" and method == "GET":
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00"})
        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/operations/item-templates" and method == "GET":
            token = ((query.get("q") or [""])[0]).strip().casefold()
            if not token:
                items = templates
            else:
                items = [
                    item for item in templates
                    if token in item["name"].casefold() or token in (item.get("shop_name") or "").casefold()
                ]
            return json_response(route, {"items": items, "total": len(items), "page": 1, "page_size": 20})

        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page()
        page.route("**/api/v1/**", handler)
        try:
            yield page
        finally:
            browser.close()


@pytest.mark.e2e
def test_receipt_picker_store_scoped_and_optimistic_create(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
    page.goto(f"{static_server_url}/static/index.html")

    page.click("#devLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")

    page.check("#opReceiptEnabled")
    page.wait_for_selector("#opReceiptFields:not(.hidden)")

    first_row = page.locator(".receipt-item-row").first
    first_row.locator('[data-receipt-field="shop_name"]').fill("Соседи")
    first_row.locator('[data-receipt-field="name"]').click()
    page.wait_for_selector('.receipt-item-row:first-child .receipt-name-picker:not(.hidden)')
    first_name_picker = first_row.locator(".receipt-name-picker")
    assert first_name_picker.locator('.chip-btn:has-text("Ротманс")').first.is_visible()
    assert first_name_picker.locator('.chip-btn:has-text("Хлеб")').count() == 0

    first_row.locator('[data-receipt-field="name"]').fill("Чипсы Лейс")
    page.locator('button[data-receipt-create-name="Чипсы Лейс"]').first.click()
    page.wait_for_timeout(100)

    second_row = page.locator(".receipt-item-row").nth(1)
    second_row.locator('[data-receipt-field="shop_name"]').fill("Соседи")
    second_row.locator('[data-receipt-field="name"]').click()
    page.wait_for_selector('.receipt-item-row:nth-child(2) .receipt-name-picker:not(.hidden)')
    second_name_picker = second_row.locator(".receipt-name-picker")
    assert second_name_picker.locator('.chip-btn:has-text("Чипсы Лейс")').first.is_visible()
    assert second_name_picker.locator('.chip-btn:has-text("Ротманс")').first.is_visible()

    page.locator("#createTitle").click()
    page.wait_for_timeout(100)
    assert second_name_picker.is_hidden()

    second_row.locator('[data-receipt-field="shop_name"]').fill("Евроопт")
    second_row.locator('[data-receipt-field="name"]').click()
    page.wait_for_selector('.receipt-item-row:nth-child(2) .receipt-name-picker:not(.hidden)')
    assert second_name_picker.locator('.chip-btn:has-text("Хлеб")').first.is_visible()
    assert second_name_picker.locator('.chip-btn:has-text("Чипсы Лейс")').count() == 0
