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


def _login(page):
    page.evaluate("() => window.App.getRuntimeModule('session')?.refreshTelegramLoginUi?.()")
    try:
        page.locator("#telegramLoginBtn").wait_for(state="visible", timeout=1200)
        page.click("#telegramLoginBtn")
        page.wait_for_selector("#appShell:not(.hidden)")
    except Exception:
        page.wait_for_selector("#appShell:not(.hidden)")


def _ensure_categories_loaded(page):
    page.evaluate("() => window.App.getRuntimeModule('category-actions')?.loadCategories?.()")
    page.wait_for_function("() => (window.App?.state?.categories || []).length >= 3")


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
            "ui": {
                "active_section": "dashboard",
                "timezone": "Europe/Moscow",
                "item_catalog_sources": ["Пустой источник"],
            },
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
        {
            "id": 102,
            "name": "Транспорт",
            "icon": "🚌",
            "kind": "expense",
            "group_id": None,
            "group_name": None,
            "group_icon": None,
            "group_accent_color": None,
            "is_system": False,
        },
        {
            "id": 103,
            "name": "Кофе",
            "icon": "☕",
            "kind": "expense",
            "group_id": None,
            "group_name": None,
            "group_icon": None,
            "group_accent_color": None,
            "is_system": False,
        },
    ]

    brands = [
        {"id": 201, "name": "Vici", "accent_color": "#35B8D4", "is_archived": False},
        {"id": 202, "name": "Савушкин", "accent_color": "#E7B349", "is_archived": False},
    ]

    templates = [
        {
            "id": 1,
            "shop_name": "Соседи",
            "name": "Ротманс",
            "brand_id": 201,
            "brand_name": "Vici",
            "brand_accent_color": "#35B8D4",
            "last_category_id": 101,
            "latest_unit_price": "6.60",
        },
        {
            "id": 2,
            "shop_name": "Евроопт",
            "name": "Хлеб",
            "brand_id": 202,
            "brand_name": "Савушкин",
            "brand_accent_color": "#E7B349",
            "latest_unit_price": "2.20",
        },
    ]
    templates.extend(
        {
            "id": idx,
            "shop_name": "Дальний источник" if idx == 125 else f"Источник {idx:03d}",
            "name": "Дальняя позиция" if idx == 125 else f"Позиция {idx:03d}",
            "latest_unit_price": "1.00",
        }
        for idx in range(3, 128)
    )
    templates.append(
        {
            "id": 128,
            "shop_name": "Green",
            "name": "Крабовые палочки охлаждённые из сурими с мясом снежного краба в сливочной заливке — очень длинное полное название позиции",
            "brand_id": 201,
            "brand_name": "Vici",
            "brand_accent_color": "#35B8D4",
            "last_category_id": 101,
            "latest_unit_price": "5.39",
        }
    )

    templates.append(
        {
            "id": 129,
            "shop_name": "Архивный источник",
            "name": "Архивная позиция",
            "brand_id": 203,
            "brand_name": "Архивный бренд",
            "brand_accent_color": "#777777",
            "brand_is_archived": True,
            "last_category_id": 101,
            "latest_unit_price": "4.20",
        }
    )

    sources = [
        {"id": 301, "name": "Пустой источник", "image_id": None, "is_archived": False},
        {"id": 302, "name": "Соседи", "image_id": None, "is_archived": False},
        {"id": 303, "name": "Евроопт", "image_id": None, "is_archived": False},
        {"id": 304, "name": "Green", "image_id": 9304, "is_archived": False},
        {"id": 305, "name": "Дальний источник", "image_id": None, "is_archived": False},
        {"id": 306, "name": "Архивный источник", "image_id": None, "is_archived": False},
    ]
    source_by_name = {source["name"]: source for source in sources}
    for item in templates:
        source = source_by_name.get(item.get("shop_name"))
        if source:
            item["source_id"] = source["id"]
            item["source_name"] = source["name"]
            item["source_image_id"] = source["image_id"]
    templates[-2]["image_id"] = 9128
    templates[-2]["brand_image_id"] = 9201
    brands[0]["image_id"] = 9201

    def source_payload(source: dict) -> dict:
        return {
            **source,
            "positions_count": len(
                [item for item in templates if int(item.get("source_id") or 0) == int(source["id"])]
            ),
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
        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "Receipt User", "username": "receipt_user", "status": "approved", "is_admin": False})
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
        if path == "/api/v1/operations/item-brands" and method == "GET":
            return json_response(route, {"items": brands, "total": len(brands), "page": 1, "page_size": 100})
        if path == "/api/v1/operations/item-sources" and method == "GET":
            active_sources = [source_payload(source) for source in sources if not source["is_archived"]]
            return json_response(
                route,
                {"items": active_sources, "total": len(active_sources), "page": 1, "page_size": 500},
            )
        if path.startswith("/api/v1/operations/item-sources/") and method == "DELETE":
            source_id = int(path.rsplit("/", 1)[-1])
            source = next((row for row in sources if int(row["id"]) == source_id), None)
            if source is None:
                return json_response(route, {"detail": "not found"}, status=404)
            source["is_archived"] = True
            templates[:] = [
                item for item in templates if int(item.get("source_id") or 0) != source_id
            ]
            return route.fulfill(status=204, body="")
        if path == "/api/v1/operations/item-templates" and method == "GET":
            token = ((query.get("q") or [""])[0]).strip().casefold()
            if not token:
                items = templates
            else:
                items = [
                    item for item in templates
                    if token in item["name"].casefold() or token in (item.get("shop_name") or "").casefold()
                ]
            page = int((query.get("page") or ["1"])[0])
            page_size = int((query.get("page_size") or ["20"])[0])
            start = (page - 1) * page_size
            end = start + page_size
            return json_response(route, {"items": items[start:end], "total": len(items), "page": page, "page_size": page_size})
        if path.startswith("/api/v1/operations/media/") and method == "GET":
            return route.fulfill(
                status=200,
                content_type="image/svg+xml",
                body='<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="#5fd3bc"/></svg>',
            )
        if path.startswith("/api/v1/operations/item-templates/") and method == "GET":
            template_id = int(path.rsplit("/", 1)[-1])
            item = next((row for row in templates if int(row["id"]) == template_id), None)
            if item is None:
                return json_response(route, {"detail": "not found"}, status=404)
            return json_response(
                route,
                {
                    **item,
                    "recommendation_enabled": False,
                    "recommendation_mode": "manual",
                    "recommendation_base_quantity": "1.000",
                },
            )
        if path.startswith("/api/v1/operations/item-templates/") and method == "PATCH":
            template_id = int(path.rsplit("/", 1)[-1])
            item = next((row for row in templates if int(row["id"]) == template_id), None)
            if item is None:
                return json_response(route, {"detail": "not found"}, status=404)
            item.update(json.loads(request.post_data or "{}"))
            return json_response(route, item)
        if path.startswith("/api/v1/operations/item-templates/") and method == "DELETE":
            template_id = int(path.rsplit("/", 1)[-1])
            templates[:] = [row for row in templates if int(row["id"]) != template_id]
            return route.fulfill(status=204, body="")

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


@pytest.mark.e2e
def test_receipt_picker_store_scoped_and_optimistic_create(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)
    _ensure_categories_loaded(page)
    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")

    page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
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
    assert second_row.locator('[data-receipt-field="shop_name"]').input_value() == "Соседи"
    second_row.locator('[data-receipt-field="name"]').click()
    page.wait_for_selector('.receipt-item-row:nth-child(2) .receipt-name-picker:not(.hidden)')
    second_name_picker = second_row.locator(".receipt-name-picker")
    assert second_name_picker.locator('.chip-btn:has-text("Чипсы Лейс")').first.is_visible()
    assert second_name_picker.locator('.chip-btn:has-text("Ротманс")').first.is_visible()

    page.locator("#createTitle").click()
    page.wait_for_timeout(100)
    assert second_name_picker.is_hidden()

    second_row.locator('[data-receipt-field="shop_name"]').fill("Евроопт")
    assert second_row.locator('[data-receipt-field="shop_name"]').input_value() == "Евроопт"
    second_row.locator('[data-receipt-field="name"]').click()
    page.wait_for_selector('.receipt-item-row:nth-child(2) .receipt-name-picker:not(.hidden)')
    assert second_name_picker.locator('.chip-btn:has-text("Хлеб")').first.is_visible()
    assert second_name_picker.locator('.chip-btn:has-text("Чипсы Лейс")').count() == 0

    first_row.locator('[data-receipt-field="shop_name"]').fill("Корона")
    assert second_row.locator('[data-receipt-field="shop_name"]').input_value() == "Евроопт"


@pytest.mark.e2e
def test_receipt_brand_picker_long_name_and_mobile_layout(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
    page.set_viewport_size({"width": 1380, "height": 900})
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
    _login(page)
    _ensure_categories_loaded(page)
    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
    page.wait_for_selector("#opReceiptFields:not(.hidden)")

    first_row = page.locator("#receiptItemsList .receipt-item-row").first
    brand_input = first_row.locator('[data-receipt-field="brand_search"]')
    brand_input.click()
    page.wait_for_selector('.receipt-brand-picker:not(.hidden) button[data-receipt-brand-id="201"]')
    first_row.locator('button[data-receipt-brand-id="201"]').click()
    assert brand_input.input_value() == "Vici"

    name_input = first_row.locator('[data-receipt-field="name"]')
    name_input.click()
    page.wait_for_selector('.receipt-name-picker:not(.hidden) button[data-receipt-template-id="128"]')
    assert first_row.locator('button[data-receipt-template-id="2"]').count() == 0
    long_name = "Крабовые палочки охлаждённые из сурими с мясом снежного краба в сливочной заливке — очень длинное полное название позиции"
    long_suggestion = first_row.locator('button[data-receipt-template-id="128"]')
    assert long_suggestion.get_attribute("title") == long_name
    assert long_name in long_suggestion.inner_text()
    long_suggestion.click()

    assert name_input.input_value() == long_name
    assert name_input.get_attribute("title") == long_name
    name_geometry = name_input.evaluate(
        """
        node => ({
          height: node.getBoundingClientRect().height,
          maxHeight: parseFloat(getComputedStyle(node).maxHeight),
          scrollHeight: node.scrollHeight,
        })
        """
    )
    assert name_geometry["height"] > 44
    assert name_geometry["height"] <= name_geometry["maxHeight"] + 1

    desktop_geometry = first_row.evaluate(
        """
        node => {
          const selectors = {
            source: '.receipt-shop-cell',
            brand: '.receipt-brand-cell',
            name: '.receipt-name-cell',
            category: '.receipt-category-cell',
            price: '.receipt-price-cell',
            quantity: '.receipt-quantity-cell',
            total: '.receipt-line-total',
            remove: '.receipt-remove-btn',
          };
          const entries = Object.entries(selectors).map(([key, selector]) => {
            const rect = node.querySelector(selector).getBoundingClientRect();
            return [key, { top: rect.top, width: rect.width }];
          });
          const rects = Object.fromEntries(entries);
          const tops = entries.map(([, rect]) => rect.top);
          return {
            clientWidth: node.clientWidth,
            scrollWidth: node.scrollWidth,
            topSpread: Math.max(...tops) - Math.min(...tops),
            identityDisplay: getComputedStyle(node.querySelector('.receipt-item-identity')).display,
            moneyDisplay: getComputedStyle(node.querySelector('.receipt-item-money')).display,
            columns: getComputedStyle(node).gridTemplateColumns,
            widths: Object.fromEntries(Object.entries(rects).map(([key, rect]) => [key, rect.width])),
            unitPriceWidth: node.querySelector('[data-receipt-field="unit_price"]').getBoundingClientRect().width,
          };
        }
        """
    )
    assert desktop_geometry["scrollWidth"] <= desktop_geometry["clientWidth"] + 2
    assert desktop_geometry["topSpread"] <= 2
    assert desktop_geometry["identityDisplay"] == "contents"
    assert desktop_geometry["moneyDisplay"] == "contents"
    assert len(desktop_geometry["columns"].split()) == 8
    assert desktop_geometry["widths"]["source"] <= 114
    assert desktop_geometry["widths"]["brand"] <= 102
    assert 315 <= desktop_geometry["widths"]["name"] <= 345
    assert desktop_geometry["widths"]["category"] <= 134
    assert desktop_geometry["widths"]["quantity"] <= 82
    assert desktop_geometry["unitPriceWidth"] <= 106
    assert desktop_geometry["widths"]["price"] > desktop_geometry["unitPriceWidth"]

    # Supporting identity fields stay compact when the modal grows. The spare
    # width belongs to the price/discount area, while the price input itself
    # remains short and the position keeps its useful reading width.
    page.set_viewport_size({"width": 1260, "height": 900})
    page.wait_for_timeout(80)
    compact_geometry = first_row.evaluate(
        """
        node => {
          const width = (selector) => node.querySelector(selector).getBoundingClientRect().width;
          return {
            row: node.getBoundingClientRect().width,
            source: width('.receipt-shop-cell'),
            brand: width('.receipt-brand-cell'),
            name: width('.receipt-name-cell'),
            category: width('.receipt-category-cell'),
            price: width('.receipt-price-cell'),
            quantity: width('.receipt-quantity-cell'),
            unitPrice: width('[data-receipt-field="unit_price"]'),
          };
        }
        """
    )
    page.set_viewport_size({"width": 1380, "height": 900})
    page.wait_for_timeout(80)
    row_growth = desktop_geometry["clientWidth"] - compact_geometry["row"]
    assert row_growth > 60
    for field in ("source", "brand", "name", "category", "quantity"):
        assert abs(desktop_geometry["widths"][field] - compact_geometry[field]) <= 16
    assert desktop_geometry["widths"]["price"] - compact_geometry["price"] >= row_growth * 0.7
    assert abs(desktop_geometry["unitPriceWidth"] - compact_geometry["unitPrice"]) <= 8

    first_row.locator(".receipt-discount-toggle").click()
    page.wait_for_selector("#receiptItemsList .receipt-item-row.receipt-item-row-discounted")
    discounted_geometry = first_row.evaluate(
        """
        node => {
          const price = node.querySelector('.receipt-price-cell');
          const inputs = [...price.querySelectorAll('.receipt-price-field input')];
          return {
            rowClientWidth: node.clientWidth,
            rowScrollWidth: node.scrollWidth,
            priceClientWidth: price.clientWidth,
            priceScrollWidth: price.scrollWidth,
            priceWidth: price.getBoundingClientRect().width,
            nameWidth: node.querySelector('.receipt-name-cell').getBoundingClientRect().width,
            inputWidths: inputs.map((input) => input.getBoundingClientRect().width),
          };
        }
        """
    )
    assert discounted_geometry["rowScrollWidth"] <= discounted_geometry["rowClientWidth"] + 2
    assert discounted_geometry["priceScrollWidth"] <= discounted_geometry["priceClientWidth"] + 2
    assert discounted_geometry["priceWidth"] > discounted_geometry["nameWidth"]
    assert len(discounted_geometry["inputWidths"]) == 2
    assert max(discounted_geometry["inputWidths"]) <= 106
    first_row.locator(".receipt-discount-toggle").click()
    assert "receipt-item-row-discounted" not in (first_row.get_attribute("class") or "")

    second_row = page.locator("#receiptItemsList .receipt-item-row").nth(1)
    assert second_row.locator('[data-receipt-field="shop_name"]').input_value() == "Green"
    assert second_row.locator('[data-receipt-field="brand_search"]').input_value() == ""

    payload = page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert payload[0]["template_id"] == 128
    assert "brand_id" not in payload[0]

    # Typing into the brand search is not an assignment. On blur the saved
    # template brand is restored and the payload stays untouched.
    brand_input.fill("Савуш")
    name_input.focus()
    page.wait_for_timeout(50)
    assert brand_input.input_value() == "Vici"
    search_only_payload = page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert "brand_id" not in search_only_payload[0]

    brand_input.click()
    first_row.locator("button[data-receipt-brand-clear]").click()
    cleared_payload = page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert cleared_payload[0]["template_id"] == 128
    assert cleared_payload[0]["brand_id"] is None

    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(120)
    mobile_positions = first_row.evaluate(
        """
        node => {
          const top = (selector) => node.querySelector(selector).getBoundingClientRect().top;
          return {
            source: top('.receipt-shop-cell'),
            brand: top('.receipt-brand-cell'),
            name: top('.receipt-name-cell'),
            category: top('.receipt-category-cell'),
            price: top('.receipt-price-cell'),
            quantity: top('.receipt-quantity-cell'),
          };
        }
        """
    )
    assert mobile_positions["source"] < mobile_positions["brand"]
    assert mobile_positions["brand"] < mobile_positions["name"]
    assert mobile_positions["name"] < mobile_positions["category"]
    assert mobile_positions["category"] < mobile_positions["price"]
    assert mobile_positions["price"] < mobile_positions["quantity"]

    page.evaluate(
        """
        () => {
          window.App.actions.closeCreateModal();
          window.App.actions.openOperationReceiptModal({
            id: 77,
            kind: 'expense',
            amount: '5.39',
            currency: 'BYN',
            base_currency: 'BYN',
            operation_date: '2026-09-04',
            receipt_items: [{
              brand_id: 201,
              brand_name: 'Vici',
              brand_accent_color: '#35B8D4',
              name: 'Крабовые палочки охлаждённые из сурими с мясом снежного краба',
              quantity: '1',
              unit_price: '5.39',
              line_total: '5.39',
            }],
          });
        }
        """
    )
    page.wait_for_selector("#operationReceiptModal:not(.hidden)")
    assert page.locator("#operationReceiptItems .operation-receipt-brand").inner_text() == "Vici"
    receipt_title = page.locator("#operationReceiptItems .operation-receipt-title strong")
    assert receipt_title.get_attribute("title") == "Крабовые палочки охлаждённые из сурими с мясом снежного краба"


@pytest.mark.e2e
def test_receipt_thumbnail_opens_nested_item_card_and_live_syncs_saved_item(
    static_server_url: str,
    page_with_receipt_api_mock,
):
    page = page_with_receipt_api_mock
    page.set_viewport_size({"width": 1280, "height": 900})
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
    _login(page)
    _ensure_categories_loaded(page)

    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
    first_row = page.locator("#receiptItemsList .receipt-item-row").first
    first_row.locator('[data-receipt-field="shop_name"]').fill("Green")

    with page.expect_request(
        lambda request: "/api/v1/operations/media/9128/thumb" in request.url
    ) as image_request:
        first_row.locator('[data-receipt-field="name"]').click()
        page.wait_for_selector(
            '.receipt-name-picker:not(.hidden) button[data-receipt-template-id="128"]'
        )
    assert image_request.value.headers.get("authorization") == "Bearer e2e-token"
    expect(
        first_row.locator(
            'button[data-receipt-template-id="128"] [data-catalog-media-id="9128"]'
        )
    ).to_be_visible()
    first_row.locator('button[data-receipt-template-id="128"]').click()
    first_row.locator('[data-receipt-field="quantity"]').fill("2")
    expect(first_row.locator('[data-open-receipt-template-card="128"]')).to_have_count(2)

    first_row.locator(".receipt-template-card-btn").click()
    expect(page.locator("#itemTemplateModal")).to_be_visible()
    expect(page.locator("#createModal")).to_be_visible()
    stack = page.evaluate(
        """
        () => ({
          base: Number(document.querySelector('#createModal').style.zIndex || 0),
          item: Number(document.querySelector('#itemTemplateModal').style.zIndex || 0),
        })
        """
    )
    assert stack["item"] > stack["base"]

    geometry = page.evaluate(
        """
        () => {
          const modal = document.querySelector('#itemTemplateModal .modal-card');
          const grid = document.querySelector('.item-template-price-grid');
          const price = document.querySelector('#itemTemplatePriceField');
          const date = document.querySelector('#itemTemplatePriceDateField');
          return {
            modalClientWidth: modal.clientWidth,
            modalScrollWidth: modal.scrollWidth,
            priceWidth: price.getBoundingClientRect().width,
            dateWidth: date.getBoundingClientRect().width,
            priceTop: price.getBoundingClientRect().top,
            dateTop: date.getBoundingClientRect().top,
            columns: getComputedStyle(grid).gridTemplateColumns,
          };
        }
        """
    )
    assert geometry["modalScrollWidth"] <= geometry["modalClientWidth"] + 2
    assert geometry["priceWidth"] >= 176
    assert geometry["dateWidth"] >= 280
    assert abs(geometry["priceTop"] - geometry["dateTop"]) <= 2
    assert len(geometry["columns"].split()) == 2

    updated_name = "Крабовые палочки Vici — обновлённая карточка"
    page.fill("#itemTemplateName", updated_name)
    page.click("#submitItemTemplateBtn")
    expect(first_row.locator('[data-receipt-field="name"]')).to_have_value(updated_name)
    expect(first_row.locator('[data-receipt-field="quantity"]')).to_have_value("2")
    expect(page.locator("#itemTemplateModal")).to_be_visible()

    page.click("#closeItemTemplateModalBtn")
    expect(page.locator("#itemTemplateModal")).to_be_hidden()
    expect(page.locator("#createModal")).to_be_visible()
    assert page.locator("#createModal").evaluate(
        "node => node.classList.contains('modal-front')"
    )


@pytest.mark.e2e
def test_cancelled_receipt_brand_change_does_not_mutate_template_hint(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)

    def open_receipt():
        page.click("#addOperationCta")
        page.wait_for_selector("#createModal:not(.hidden)")
        page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
        page.wait_for_selector("#opReceiptFields:not(.hidden)")

    def select_saved_template():
        row = page.locator("#receiptItemsList .receipt-item-row").first
        row.locator('[data-receipt-field="shop_name"]').fill("Соседи")
        row.locator('[data-receipt-field="name"]').click()
        page.wait_for_selector('.receipt-name-picker:not(.hidden) button[data-receipt-template-id="1"]')
        row.locator('button[data-receipt-template-id="1"]').click()
        return row

    open_receipt()
    row = select_saved_template()
    assert row.locator('[data-receipt-field="brand_search"]').input_value() == "Vici"
    row.locator('[data-receipt-field="brand_search"]').click()
    page.wait_for_selector('.receipt-brand-picker:not(.hidden) button[data-receipt-brand-id="202"]')
    row.locator('button[data-receipt-brand-id="202"]').click()
    assert row.locator('[data-receipt-field="brand_search"]').input_value() == "Савушкин"

    page.click("#closeCreateModalBtn")
    page.wait_for_selector("#createModal", state="hidden")
    open_receipt()
    reopened_row = select_saved_template()
    assert reopened_row.locator('[data-receipt-field="brand_search"]').input_value() == "Vici"
    payload = page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert payload[0]["template_id"] == 1
    assert "brand_id" not in payload[0]


@pytest.mark.e2e
def test_receipt_brand_follows_new_identity_and_archived_brand_is_cleared(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)

    def open_receipt():
        page.click("#addOperationCta")
        page.wait_for_selector("#createModal:not(.hidden)")
        page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
        page.wait_for_selector("#opReceiptFields:not(.hidden)")
        return page.locator("#receiptItemsList .receipt-item-row").first

    row = open_receipt()
    row.locator('[data-receipt-field="shop_name"]').fill("Соседи")
    row.locator('[data-receipt-field="name"]').click()
    page.wait_for_selector('.receipt-name-picker:not(.hidden) button[data-receipt-template-id="1"]')
    row.locator('button[data-receipt-template-id="1"]').click()
    row.locator('[data-receipt-field="name"]').fill("Ротманс новое название")

    renamed_payload = page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert "template_id" not in renamed_payload[0]
    assert renamed_payload[0]["brand_id"] == 201
    assert row.locator('[data-receipt-field="brand_search"]').input_value() == "Vici"

    page.click("#closeCreateModalBtn")
    page.wait_for_selector("#createModal", state="hidden")

    archived_row = open_receipt()
    archived_row.locator('[data-receipt-field="shop_name"]').fill("Архивный источник")
    archived_row.locator('[data-receipt-field="name"]').click()
    page.wait_for_selector('.receipt-name-picker:not(.hidden) button[data-receipt-template-id="129"]')
    archived_row.locator('button[data-receipt-template-id="129"]').click()
    assert archived_row.locator('[data-receipt-field="brand_search"]').input_value() == "Архивный бренд"

    archived_row.locator('[data-receipt-field="name"]').fill("Новая позиция вместо архивной")
    archived_payload = page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert "template_id" not in archived_payload[0]
    assert archived_payload[0]["brand_id"] is None
    assert archived_row.locator('[data-receipt-field="brand_search"]').input_value() == ""


@pytest.mark.e2e
def test_receipt_picker_loads_catalog_sources_and_templates_beyond_first_page(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)
    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
    page.wait_for_selector("#opReceiptFields:not(.hidden)")

    first_row = page.locator(".receipt-item-row").first
    first_row.locator('[data-receipt-field="shop_name"]').click()
    page.wait_for_selector('.receipt-item-row:first-child .receipt-shop-picker:not(.hidden)')
    assert first_row.locator('.receipt-shop-picker .chip-btn:has-text("Пустой источник")').first.is_visible()
    chip_geometry = first_row.locator(".receipt-shop-picker").evaluate(
        """
        node => ({
          gap: parseFloat(getComputedStyle(node).rowGap || '0'),
          heights: [...node.querySelectorAll('.chip-btn')].slice(0, 12).map((chip) => chip.getBoundingClientRect().height),
        })
        """
    )
    assert chip_geometry["gap"] <= 8
    assert chip_geometry["heights"]
    assert max(chip_geometry["heights"]) <= 32

    first_row.locator('[data-receipt-field="shop_name"]').fill("Дальний")
    page.wait_for_selector('.receipt-item-row:first-child .receipt-shop-picker:not(.hidden)')
    assert first_row.locator('.receipt-shop-picker .chip-btn:has-text("Дальний источник")').first.is_visible()
    first_row.locator('.receipt-shop-picker .chip-btn:has-text("Дальний источник")').first.click()

    first_row.locator('[data-receipt-field="name"]').click()
    page.wait_for_selector('.receipt-item-row:first-child .receipt-name-picker:not(.hidden)')
    assert first_row.locator('.receipt-name-picker .chip-btn:has-text("Дальняя позиция")').first.is_visible()


@pytest.mark.e2e
def test_pull_receipt_total_clears_discrepancy_after_multiple_rows(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)
    _ensure_categories_loaded(page)
    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
    page.wait_for_selector("#opReceiptFields:not(.hidden)")

    first_row = page.locator(".receipt-item-row").nth(0)
    first_row.locator('[data-receipt-field="shop_name"]').fill("Green")
    first_row.locator('[data-receipt-field="name"]').fill("Кофе")
    first_row.locator('[data-receipt-field="quantity"]').fill("3")
    first_row.locator('[data-receipt-field="unit_price"]').fill("7.70")

    second_row = page.locator(".receipt-item-row").nth(1)
    second_row.locator('[data-receipt-field="shop_name"]').fill("Green")
    second_row.locator('[data-receipt-field="name"]').fill("Сироп")
    second_row.locator('[data-receipt-field="quantity"]').fill("2")
    second_row.locator('[data-receipt-field="unit_price"]').fill("5.11")

    page.evaluate(
        """
        () => {
          window.App.state.createReceiptItems[0].category_id = 101;
          window.App.state.createReceiptItems[1].category_id = 102;
          window.App.actions.renderReceiptItems('create');
          window.App.actions.updateCreatePreview();
        }
        """
    )
    preview_geometry = page.locator("#createPreviewBody .preview-cell-btn").nth(2).evaluate(
        """
        node => {
          const bounds = node.getBoundingClientRect();
          const chips = [...node.querySelectorAll('.category-chip, .meta-chip')].map((chip) => {
            const rect = chip.getBoundingClientRect();
            return { top: rect.top, bottom: rect.bottom };
          });
          return {
            top: bounds.top,
            bottom: bounds.bottom,
            clientHeight: node.clientHeight,
            scrollHeight: node.scrollHeight,
            chips,
          };
        }
        """
    )
    assert preview_geometry["scrollHeight"] <= preview_geometry["clientHeight"] + 1
    assert all(
        preview_geometry["top"] - 1 <= chip["top"]
        and chip["bottom"] <= preview_geometry["bottom"] + 1
        for chip in preview_geometry["chips"]
    )

    page.locator("#opAmount").fill("999.00")
    page.locator("#pullReceiptTotalBtn").click()

    assert page.locator("#opAmount").input_value() == "33.32"
    assert "33,32" in page.locator("#receiptTotalValue").inner_text()
    assert "0,00" in page.locator("#receiptDiffValue").inner_text()
    assert "receipt-diff-warn" not in (page.locator("#receiptDiffValue").get_attribute("class") or "")
    page.locator("#createPreviewBody").scroll_into_view_if_needed()
    page.screenshot(path="/tmp/finasist-create-receipt-preview.png")


@pytest.mark.e2e
def test_item_catalog_loads_templates_beyond_first_page(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)
    page.click("button[data-section='item_catalog']")
    page.wait_for_selector("#itemCatalogSection:not(.hidden)")
    page.wait_for_function("() => (window.App?.state?.itemCatalogItems || []).length >= 127")

    assert page.locator("#itemCatalogBody").get_by_text("Дальняя позиция").first.is_visible()


@pytest.mark.e2e
def test_item_catalog_shows_and_edits_template_category(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)
    _ensure_categories_loaded(page)
    page.click("button[data-section='item_catalog']")
    page.wait_for_selector("#itemCatalogSection:not(.hidden)")

    row = page.locator('tr[data-item-template-open-id="1"]')
    assert "Еда" in (row.text_content() or "")
    row.click()
    page.wait_for_selector("#itemTemplateModal:not(.hidden)")
    assert page.locator("#itemTemplateCategorySearch").input_value() == "Еда"

    page.click("#itemTemplateCategorySearch")
    page.locator('#itemTemplateCategoryAll button[data-item-template-category-id="102"]').click()
    page.click("#submitItemTemplateBtn")
    page.wait_for_function(
        "() => (window.App.state.itemCatalogItems || []).find((item) => Number(item.id) === 1)?.last_category_id === 102"
    )

    assert "Транспорт" in (page.locator('tr[data-item-template-open-id="1"]').text_content() or "")


@pytest.mark.e2e
def test_item_catalog_price_update_is_applied_to_catalog_and_receipt_hints(
    static_server_url: str,
    page_with_receipt_api_mock,
):
    page = page_with_receipt_api_mock
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
    _login(page)
    _ensure_categories_loaded(page)
    page.click("button[data-section='item_catalog']")
    page.wait_for_selector("#itemCatalogSection:not(.hidden)")
    page.evaluate(
        """
        () => {
          window.App.state.receiptTemplateHints = [{
            id: 1,
            shop_name: "Соседи",
            shop_name_ci: "соседи",
            name: "Ротманс",
            name_ci: "ротманс",
            last_category_id: 101,
            latest_unit_price: 6.60,
          }];
        }
        """
    )

    page.locator('tr[data-item-template-open-id="1"]').click()
    page.wait_for_selector("#itemTemplateModal:not(.hidden)")
    page.fill("#itemTemplatePrice", "7.25")
    page.evaluate(
        "() => window.App.core.syncDateFieldValue(document.querySelector('#itemTemplatePriceDate'), '2026-08-16')"
    )
    page.click("#submitItemTemplateBtn")

    page.wait_for_function(
        "() => Number((window.App.state.itemCatalogItems || []).find((item) => Number(item.id) === 1)?.latest_unit_price) === 7.25"
    )
    assert "7,25" in (page.locator('tr[data-item-template-open-id="1"]').text_content() or "")
    assert page.evaluate(
        "() => Number((window.App.state.receiptTemplateHints || []).find((item) => Number(item.id) === 1)?.latest_unit_price)"
    ) == 7.25


@pytest.mark.e2e
def test_deleting_item_catalog_source_archives_its_templates_instead_of_moving_them(
    static_server_url: str,
    page_with_receipt_api_mock,
):
    page = page_with_receipt_api_mock
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
    _login(page)
    page.click("button[data-section='item_catalog']")
    page.wait_for_function("() => (window.App?.state?.itemCatalogItems || []).length >= 127")

    page.evaluate("() => window.App.actions.deleteItemSourceFlow('Соседи')")
    page.wait_for_selector("#confirmModal:not(.hidden)")
    assert "1 поз." in page.locator("#confirmText").inner_text()
    page.click("#confirmDeleteBtn")
    page.wait_for_function(
        "() => !(window.App?.state?.itemCatalogItems || []).some((item) => item.shop_name === 'Соседи')"
    )

    assert page.locator('tr[data-item-template-open-id="1"]').count() == 0
    assert page.locator('tr[data-item-template-open-id="2"]').count() == 1


@pytest.mark.e2e
def test_receipt_category_picker_closes_on_outside_click(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)
    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
    page.wait_for_selector("#opReceiptFields:not(.hidden)")

    first_row = page.locator(".receipt-item-row").first
    first_row.locator('[data-receipt-field="category_search"]').click()
    page.wait_for_selector('.receipt-item-row:first-child .receipt-category-picker:not(.hidden)')

    page.click("#createTitle")
    page.wait_for_timeout(100)

    assert first_row.locator(".receipt-category-picker").is_hidden()


@pytest.mark.e2e
def test_mobile_create_modal_preview_stays_above_sticky_cta(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)
    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")

    page.fill("#opDate", "2026-03-08")
    page.fill("#opAmount", "123.45")
    page.fill("#opNote", "Мобильная проверка превью")
    page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
    page.wait_for_selector("#opReceiptFields:not(.hidden)")

    first_row = page.locator(".receipt-item-row").first
    first_row.locator('[data-receipt-field="shop_name"]').fill("Соседи")
    first_row.locator('[data-receipt-field="name"]').fill("Длинная тестовая позиция")
    first_row.locator('[data-receipt-field="quantity"]').fill("2")
    first_row.locator('[data-receipt-field="unit_price"]').fill("11.20")
    page.wait_for_timeout(150)

    page.evaluate(
        """
        () => {
          const modalCard = document.querySelector('#createModal .modal-card');
          if (modalCard) {
            modalCard.scrollTop = modalCard.scrollHeight;
          }
        }
        """
    )
    page.wait_for_timeout(200)

    geometry = page.evaluate(
        """
        () => {
          const previewRow = document.querySelector('#createPreviewBody .preview-row');
          const previewPanel = document.querySelector('#createModal .preview-panel');
          const footer = document.querySelector('#createModal .modal-footer');
          if (!previewRow || !previewPanel || !footer) {
            return null;
          }
          const previewRowRect = previewRow.getBoundingClientRect();
          const previewPanelRect = previewPanel.getBoundingClientRect();
          const footerRect = footer.getBoundingClientRect();
          return {
            previewRowTop: previewRowRect.top,
            previewRowBottom: previewRowRect.bottom,
            previewPanelTop: previewPanelRect.top,
            footerTop: footerRect.top,
            footerBottom: footerRect.bottom,
            viewportHeight: window.innerHeight,
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["previewPanelTop"] < geometry["footerTop"]
    assert geometry["previewRowTop"] < geometry["footerTop"]
    assert geometry["previewRowBottom"] <= geometry["footerTop"] + 2


@pytest.mark.e2e
def test_mobile_edit_modal_preview_stays_above_sticky_cta(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)
    _ensure_categories_loaded(page)

    page.evaluate(
        """
        () => {
          window.App.actions.openEditModal({
            id: 77,
            kind: "expense",
            category_id: 101,
            amount: "88.40",
            operation_date: "2026-03-08",
            note: "Редактирование на мобиле",
            receipt_items: [
              {
                template_id: 1,
                shop_name: "Соседи",
                name: "Большая тестовая позиция для проверки нижнего блока",
                quantity: "2",
                unit_price: "14.20",
                note: ""
              },
              {
                template_id: 2,
                shop_name: "Евроопт",
                name: "Еще одна позиция",
                quantity: "1",
                unit_price: "60.00",
                note: ""
              }
            ]
          });
        }
        """
    )
    page.wait_for_selector("#editModal:not(.hidden)")
    page.wait_for_selector("#editReceiptFields:not(.hidden)")

    page.evaluate(
        """
        () => {
          const modalCard = document.querySelector('#editModal .modal-card');
          if (modalCard) {
            modalCard.scrollTop = modalCard.scrollHeight;
          }
        }
        """
    )
    page.wait_for_timeout(200)

    geometry = page.evaluate(
        """
        () => {
          const previewRow = document.querySelector('#editPreviewBody .preview-row');
          const previewPanel = document.querySelector('#editModal .preview-panel');
          const footer = document.querySelector('#editModal .modal-footer');
          if (!previewRow || !previewPanel || !footer) {
            return null;
          }
          const previewRowRect = previewRow.getBoundingClientRect();
          const previewPanelRect = previewPanel.getBoundingClientRect();
          const footerRect = footer.getBoundingClientRect();
          return {
            previewRowTop: previewRowRect.top,
            previewRowBottom: previewRowRect.bottom,
            previewPanelTop: previewPanelRect.top,
            footerTop: footerRect.top,
            footerBottom: footerRect.bottom,
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["previewPanelTop"] < geometry["footerTop"]
    assert geometry["previewRowTop"] < geometry["footerTop"]
    assert geometry["previewRowBottom"] <= geometry["footerTop"] + 2


@pytest.mark.e2e
def test_edit_receipt_mixed_categories_keep_inheritance_and_preview_summary(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)
    _ensure_categories_loaded(page)

    page.evaluate(
        """
        () => {
          window.App.actions.openEditModal({
            id: 91,
            kind: "expense",
            category_id: 101,
            amount: "33.00",
            operation_date: "2026-03-08",
            note: "Mixed edit",
            receipt_items: [
              {
                template_id: 1,
                category_id: null,
                shop_name: "Соседи",
                name: "Булка",
                quantity: "1",
                unit_price: "8.00",
                note: ""
              },
              {
                template_id: 2,
                category_id: 102,
                shop_name: "Метро",
                name: "Проезд",
                quantity: "1",
                unit_price: "25.00",
                note: ""
              }
            ]
          });
        }
        """
    )
    page.wait_for_selector("#editModal:not(.hidden)")
    page.wait_for_selector("#editReceiptFields:not(.hidden)")

    first_row = page.locator(".receipt-item-row").first
    second_row = page.locator(".receipt-item-row").nth(1)

    expect_badge_first = first_row.locator(".receipt-category-badge")
    expect_badge_second = second_row.locator(".receipt-category-badge")
    assert expect_badge_first.is_visible()
    assert expect_badge_first.text_content().strip() == "По умолчанию"
    assert not expect_badge_second.is_visible()
    assert first_row.locator('[data-receipt-field="category_search"]').input_value() == "Еда"
    assert second_row.locator('[data-receipt-field="category_search"]').input_value() == "Транспорт"
    preview_text = page.locator("#editPreviewBody").text_content() or ""
    assert "Еда" in preview_text
    assert "Транспорт" in preview_text

    first_row.locator('[data-receipt-field="category_search"]').click()
    page.wait_for_selector('.receipt-item-row:first-child .receipt-category-picker:not(.hidden)')
    first_active = first_row.locator(".receipt-category-picker .chip-btn.active").first
    assert "Еда" in (first_active.text_content() or "")

    page.click("#editCategorySearch")
    page.wait_for_selector("#editCategoryPickerBlock:not(.hidden)")
    page.locator('#editCategoryAll button[data-category-id="103"]').click()
    page.wait_for_timeout(100)

    assert first_row.locator('[data-receipt-field="category_search"]').input_value() == "Кофе"
    assert second_row.locator('[data-receipt-field="category_search"]').input_value() == "Транспорт"
    assert expect_badge_first.is_visible()
    assert not expect_badge_second.is_visible()
    preview_text = page.locator("#editPreviewBody").text_content() or ""
    assert "Кофе" in preview_text
    assert "Транспорт" in preview_text

    second_row.locator('[data-receipt-field="category_search"]').click()
    page.wait_for_selector('.receipt-item-row:nth-child(2) .receipt-category-picker:not(.hidden)')
    second_row.locator('button[data-receipt-category-id=""]').click()
    page.wait_for_timeout(100)

    assert second_row.locator('[data-receipt-field="category_search"]').input_value() == "Кофе"
    assert expect_badge_second.is_visible()
    assert page.locator("#editPreviewBody").text_content().count("Кофе") >= 1


@pytest.mark.e2e
def test_mobile_item_template_modal_preview_stays_above_sticky_cta(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)
    page.click("#mobileNavToggleBtn")
    page.click("button[data-section='item_catalog']")
    page.wait_for_selector("#itemCatalogSection:not(.hidden)")
    page.click("#addItemTemplateCta")
    page.wait_for_selector("#itemTemplateModal:not(.hidden)")

    page.fill("#itemTemplateSourceSearch", "Соседи")
    page.fill("#itemTemplateName", "Мобильная позиция")
    page.fill("#itemTemplatePrice", "15.40")
    page.wait_for_timeout(150)

    geometry = page.evaluate(
        """
        () => {
          const previewRow = document.querySelector('#itemTemplatePreviewBody tr');
          const previewPanel = document.querySelector('#itemTemplateModal .preview-panel');
          const footer = document.querySelector('#itemTemplateModal .modal-footer');
          if (!previewRow || !previewPanel || !footer) {
            return null;
          }
          const previewRowRect = previewRow.getBoundingClientRect();
          const previewPanelRect = previewPanel.getBoundingClientRect();
          const footerRect = footer.getBoundingClientRect();
          return {
            previewRowTop: previewRowRect.top,
            previewRowBottom: previewRowRect.bottom,
            previewPanelTop: previewPanelRect.top,
            footerTop: footerRect.top,
            footerBottom: footerRect.bottom,
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["previewPanelTop"] < geometry["footerTop"]
    assert geometry["previewRowTop"] < geometry["footerTop"]
    assert geometry["previewRowBottom"] <= geometry["footerTop"] + 2


@pytest.mark.e2e
def test_mobile_source_group_modal_preview_stays_above_sticky_cta(static_server_url: str, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
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
    _login(page)
    page.click("#mobileNavToggleBtn")
    page.click("button[data-section='item_catalog']")
    page.wait_for_selector("#itemCatalogSection:not(.hidden)")
    page.click("#addItemSourceCta")
    page.wait_for_selector("#sourceGroupModal:not(.hidden)")

    page.fill("#sourceGroupName", "Новый источник на мобиле")
    page.evaluate("() => window.App.getRuntimeModule('item-catalog')?.updateSourceGroupPreview?.()")
    page.wait_for_timeout(150)

    geometry = page.evaluate(
        """
        () => {
          const previewRow = document.querySelector('#sourceGroupPreviewBody tr');
          const previewPanel = document.querySelector('#sourceGroupModal .preview-panel');
          const footer = document.querySelector('#sourceGroupModal .modal-footer');
          if (!previewRow || !previewPanel || !footer) {
            return null;
          }
          const previewRowRect = previewRow.getBoundingClientRect();
          const previewPanelRect = previewPanel.getBoundingClientRect();
          const footerRect = footer.getBoundingClientRect();
          return {
            previewRowTop: previewRowRect.top,
            previewRowBottom: previewRowRect.bottom,
            previewPanelTop: previewPanelRect.top,
            footerTop: footerRect.top,
            footerBottom: footerRect.bottom,
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["previewPanelTop"] < geometry["footerTop"]
    assert geometry["previewRowTop"] < geometry["footerTop"]
    assert geometry["previewRowBottom"] <= geometry["footerTop"] + 2
