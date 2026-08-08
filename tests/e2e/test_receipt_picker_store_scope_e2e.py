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

    templates = [
        {
            "id": 1,
            "shop_name": "Соседи",
            "name": "Ротманс",
            "last_category_id": 101,
            "latest_unit_price": "6.60",
        },
        {
            "id": 2,
            "shop_name": "Евроопт",
            "name": "Хлеб",
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
