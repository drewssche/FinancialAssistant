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


@pytest.mark.e2e
def test_create_operation_allows_receipt_only_amount(static_server_url: str):
    created_payloads: list[dict] = []

    def json_response(route, payload: dict | list, status: int = 200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def handler(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        method = request.method.upper()

        if path == "/api/v1/auth/public-config" and method == "GET":
            return json_response(route, {"telegram_bot_username": "FinanceWeaselBot", "browser_login_available": False})
        if path == "/api/v1/auth/telegram" and method == "POST":
            return json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})
        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "Receipt User", "username": "receipt_user", "status": "approved", "is_admin": False})
        if path == "/api/v1/preferences" and method == "GET":
            return json_response(route, {"preferences_version": 1, "data": {"ui": {"active_section": "dashboard", "timezone": "Europe/Moscow"}}})
        if path == "/api/v1/preferences" and method == "PUT":
            return json_response(route, {"preferences_version": 1, "data": {"ui": {"active_section": "dashboard", "timezone": "Europe/Moscow"}}})
        if path == "/api/v1/categories/groups" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/categories" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/dashboard/summary" and method == "GET":
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00"})
        if path == "/api/v1/dashboard/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/dashboard/analytics" and method == "GET":
            return json_response(route, {"points": [], "summary": {}})
        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/operations/item-templates" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
        if path == "/api/v1/operations" and method == "POST":
            payload = json.loads(request.post_data or "{}")
            created_payloads.append(payload)
            return json_response(
                route,
                {
                    "id": 1,
                    "kind": payload["kind"],
                    "amount": "15.40",
                    "operation_date": payload["operation_date"],
                    "category_id": payload["category_id"],
                    "note": payload.get("note") or "",
                    "receipt_items": [
                        {
                            "id": 1,
                            "template_id": None,
                            "shop_name": payload["receipt_items"][0].get("shop_name"),
                            "name": payload["receipt_items"][0]["name"],
                            "quantity": payload["receipt_items"][0]["quantity"],
                            "unit_price": payload["receipt_items"][0]["unit_price"],
                            "line_total": "15.40",
                            "note": None,
                        },
                    ],
                    "receipt_total": "15.40",
                    "receipt_discrepancy": "0.00",
                },
                status=201,
            )

        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page()
        page.add_init_script(
            """
            window.localStorage.setItem("access_token", "e2e-token");
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
            page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
            page.wait_for_selector("#appShell:not(.hidden)")
            page.click("#addOperationCta")
            page.wait_for_selector("#createModal:not(.hidden)")

            page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
            page.wait_for_selector("#opReceiptFields:not(.hidden)")

            first_row = page.locator(".receipt-item-row").first
            first_row.locator('[data-receipt-field="shop_name"]').fill("Соседи")
            first_row.locator('[data-receipt-field="name"]').fill("Хлеб")
            first_row.locator('[data-receipt-field="quantity"]').fill("2")
            first_row.locator('[data-receipt-field="unit_price"]').fill("7.70")

            page.click("#submitCreateOperationBtn")
            page.wait_for_timeout(300)

            assert len(created_payloads) == 1
            assert created_payloads[0]["amount"] is None
            assert created_payloads[0]["receipt_items"] == [
                {
                    "category_id": None,
                    "shop_name": "Соседи",
                    "name": "Хлеб",
                    "quantity": "2",
                    "unit_price": "7.70",
                }
            ]
        finally:
            browser.close()
