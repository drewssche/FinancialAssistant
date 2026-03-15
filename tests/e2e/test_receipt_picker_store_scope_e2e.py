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
            return json_response(route, {"items": items, "total": len(items), "page": 1, "page_size": 20})

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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")

    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")
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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")

    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")
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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")

    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.wait_for_function("() => (window.App?.state?.categories || []).length >= 3")

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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")

    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.wait_for_function("() => (window.App?.state?.categories || []).length >= 3")

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
    assert page.locator("#editPreviewBody").text_content().count("Несколько категорий") >= 1

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
    assert page.locator("#editPreviewBody").text_content().count("Несколько категорий") >= 1

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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")

    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")
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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")

    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.click("#mobileNavToggleBtn")
    page.click("button[data-section='item_catalog']")
    page.wait_for_selector("#itemCatalogSection:not(.hidden)")
    page.click("#addItemSourceCta")
    page.wait_for_selector("#sourceGroupModal:not(.hidden)")

    page.fill("#sourceGroupName", "Новый источник на мобиле")
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
