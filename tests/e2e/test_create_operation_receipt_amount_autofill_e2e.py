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
    dashboard_summary_requests = 0

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
            nonlocal dashboard_summary_requests
            dashboard_summary_requests += 1
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
                    "is_discounted": False,
                    "regular_unit_price": None,
                    "discount_type": None,
                }
            ]
            page.wait_for_timeout(500)
            assert dashboard_summary_requests >= 2
        finally:
            browser.close()


@pytest.mark.e2e
def test_create_operation_receipt_discount_math_and_type_payload(static_server_url: str):
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
            receipt_item = payload["receipt_items"][0]
            return json_response(
                route,
                {
                    "id": 1,
                    "kind": payload["kind"],
                    "amount": receipt_item["unit_price"],
                    "operation_date": payload["operation_date"],
                    "category_id": payload["category_id"],
                    "note": payload.get("note") or "",
                    "receipt_items": [
                        {
                            "id": 1,
                            "template_id": None,
                            "shop_name": receipt_item.get("shop_name"),
                            "name": receipt_item["name"],
                            "quantity": receipt_item["quantity"],
                            "unit_price": receipt_item["unit_price"],
                            "is_discounted": receipt_item["is_discounted"],
                            "regular_unit_price": receipt_item["regular_unit_price"],
                            "discount_type": receipt_item["discount_type"],
                            "line_total": receipt_item["unit_price"],
                            "note": None,
                        },
                    ],
                    "receipt_total": receipt_item["unit_price"],
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
        page = browser.new_page(viewport={"width": 1280, "height": 860})
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
            first_row.locator('[data-receipt-field="name"]').fill("Кофе")
            first_row.locator('[data-receipt-field="quantity"]').fill("1")
            unit_price = first_row.locator('[data-receipt-field="unit_price"]')
            unit_price.fill("129.90-15")
            first_row.locator('button[data-receipt-discount-toggle]').click()
            first_row.locator('button[data-receipt-discount-type="coupon"]').click()
            regular_price = first_row.locator('[data-receipt-field="regular_unit_price"]')
            regular_price.fill("129.90+0")
            first_row.locator('[data-receipt-field="name"]').click()

            assert unit_price.input_value() == "114.90"
            assert regular_price.input_value() == "129.90"
            assert first_row.locator('button[data-receipt-discount-type="coupon"]').get_attribute("aria-pressed") == "true"
            assert first_row.locator('button[data-receipt-discount-toggle]').inner_text() == "Скидка −11.5%"

            page.click("#submitCreateOperationBtn")
            page.wait_for_timeout(300)

            assert len(created_payloads) == 1
            assert created_payloads[0]["receipt_items"] == [
                {
                    "category_id": None,
                    "shop_name": "Соседи",
                    "name": "Кофе",
                    "quantity": "1",
                    "unit_price": "114.90",
                    "is_discounted": True,
                    "regular_unit_price": "129.90",
                    "discount_type": "coupon",
                }
            ]
        finally:
            browser.close()


@pytest.mark.e2e
def test_common_operation_amount_can_convert_to_single_discount_receipt(static_server_url: str):
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
            receipt_item = payload["receipt_items"][0]
            return json_response(
                route,
                {
                    "id": 1,
                    "kind": payload["kind"],
                    "amount": receipt_item["unit_price"],
                    "operation_date": payload["operation_date"],
                    "category_id": payload["category_id"],
                    "note": payload.get("note") or "",
                    "receipt_items": [
                        {
                            "id": 1,
                            "template_id": None,
                            "shop_name": receipt_item.get("shop_name"),
                            "name": receipt_item["name"],
                            "quantity": receipt_item["quantity"],
                            "unit_price": receipt_item["unit_price"],
                            "is_discounted": receipt_item["is_discounted"],
                            "regular_unit_price": receipt_item["regular_unit_price"],
                            "discount_type": receipt_item["discount_type"],
                            "line_total": receipt_item["unit_price"],
                            "note": None,
                        },
                    ],
                    "receipt_total": receipt_item["unit_price"],
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
        page = browser.new_page(viewport={"width": 1280, "height": 860})
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

            page.locator("#opAmount").fill("129.90-15")
            page.locator("#convertAmountToDiscountReceiptBtn").click()
            page.wait_for_selector("#opReceiptFields:not(.hidden)")

            assert page.locator("#opOperationMode").input_value() == "receipt"
            first_row = page.locator(".receipt-item-row").first
            assert first_row.locator('[data-receipt-field="unit_price"]').input_value() == "114.90"
            assert first_row.locator('button[data-receipt-discount-type="promo"]').get_attribute("aria-pressed") == "true"

            first_row.locator('[data-receipt-field="shop_name"]').fill("Green")
            first_row.locator('[data-receipt-field="name"]').fill("Капучино")
            first_row.locator('[data-receipt-field="regular_unit_price"]').fill("129.90")
            page.click("#submitCreateOperationBtn")
            page.wait_for_timeout(300)

            assert created_payloads[0]["amount"] is None
            assert created_payloads[0]["receipt_items"] == [
                {
                    "category_id": None,
                    "shop_name": "Green",
                    "name": "Капучино",
                    "quantity": "1",
                    "unit_price": "114.90",
                    "is_discounted": True,
                    "regular_unit_price": "129.90",
                    "discount_type": "promo",
                }
            ]
        finally:
            browser.close()
