import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest


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
def test_delete_all_categories_removes_groups_and_categories_in_one_pass(page):
    deleted_category_ids = []
    deleted_group_ids = []

    def handle_request(route):
        request = route.request
        url = request.url
        method = request.method

        if url.endswith("/api/v1/auth/public-config"):
            route.fulfill(status=200, content_type="application/json", body='{"telegram_bot_username":"FinanceWeaselBot","browser_login_available":true}')
            return
        if url.endswith("/api/v1/users/me"):
            route.fulfill(status=200, content_type="application/json", body='{"id":1,"display_name":"Admin","status":"approved","is_admin":true,"username":"owner_admin","telegram_id":"281896361"}')
            return
        if "/api/v1/preferences" in url:
            route.fulfill(status=200, content_type="application/json", body='{"data":{"ui":{}}}')
            return
        if "/api/v1/dashboard/summary" in url:
            route.fulfill(status=200, content_type="application/json", body='{"income_total":"0.00","expense_total":"0.00","balance":"0.00","debt_lend_total":"0.00","debt_borrow_total":"0.00","debt_net_total":"0.00"}')
            return
        if "/api/v1/dashboard/operations" in url or "/api/v1/dashboard/analytics" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if "/api/v1/operations?" in url or "/api/v1/debts" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if url.endswith("/api/v1/categories/groups") and method == "GET":
            route.fulfill(
                status=200,
                content_type="application/json",
                body='[{"id":7,"name":"Еда","kind":"expense","accent_color":"#ff8a3d"},{"id":8,"name":"Доходы","kind":"income","accent_color":"#49be78"}]',
            )
            return
        if "/api/v1/categories?" in url and method == "GET":
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"items":[{"id":21,"name":"Снеки","icon":null,"kind":"expense","group_id":7,"group_name":"Еда","group_icon":null,"group_accent_color":"#ff8a3d","is_system":false},{"id":22,"name":"Зарплата","icon":null,"kind":"income","group_id":8,"group_name":"Доходы","group_icon":null,"group_accent_color":"#49be78","is_system":false}],"total":2,"page":1,"page_size":20}',
            )
            return
        if url.endswith("/api/v1/categories") and method == "GET":
            route.fulfill(
                status=200,
                content_type="application/json",
                body='[{"id":21,"name":"Снеки","icon":null,"kind":"expense","group_id":7,"group_name":"Еда","group_icon":null,"group_accent_color":"#ff8a3d","is_system":false},{"id":22,"name":"Зарплата","icon":null,"kind":"income","group_id":8,"group_name":"Доходы","group_icon":null,"group_accent_color":"#49be78","is_system":false}]',
            )
            return
        if "/api/v1/categories/groups/" in url and method == "DELETE":
            deleted_group_ids.append(int(url.rsplit("/", 1)[-1]))
            route.fulfill(status=204, content_type="application/json", body="")
            return
        if "/api/v1/categories/" in url and method == "DELETE":
            deleted_category_ids.append(int(url.rsplit("/", 1)[-1]))
            route.fulfill(status=204, content_type="application/json", body="")
            return
        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/**", handle_request)
    page.add_init_script("""window.localStorage.setItem("access_token", "test-token");""")

    page.goto("http://127.0.0.1:8001/", wait_until="networkidle")
    page.locator("#mainNav button[data-section='categories']").click()
    page.locator("#deleteAllCategoriesBtn").click()
    page.locator("#confirmDeleteBtn").click()

    page.wait_for_timeout(300)

    assert deleted_category_ids == [21, 22]
    assert deleted_group_ids == [7, 8]


@pytest.mark.e2e
def test_batch_category_modal_imports_categories_with_group_fallback(page):
    created_categories = []

    def handle_request(route):
        request = route.request
        url = request.url
        method = request.method

        if url.endswith("/api/v1/auth/public-config"):
            route.fulfill(status=200, content_type="application/json", body='{"telegram_bot_username":"FinanceWeaselBot","browser_login_available":true}')
            return
        if url.endswith("/api/v1/users/me"):
            route.fulfill(status=200, content_type="application/json", body='{"id":1,"display_name":"Admin","status":"approved","is_admin":true,"username":"owner_admin","telegram_id":"281896361"}')
            return
        if "/api/v1/preferences" in url:
            route.fulfill(status=200, content_type="application/json", body='{"data":{"ui":{}}}')
            return
        if "/api/v1/dashboard/summary" in url:
            route.fulfill(status=200, content_type="application/json", body='{"income_total":"0.00","expense_total":"0.00","balance":"0.00","debt_lend_total":"0.00","debt_borrow_total":"0.00","debt_net_total":"0.00"}')
            return
        if "/api/v1/dashboard/operations" in url or "/api/v1/dashboard/analytics" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if "/api/v1/operations?" in url or "/api/v1/debts" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if url.endswith("/api/v1/categories/groups") and method == "GET":
            route.fulfill(status=200, content_type="application/json", body='[{"id":7,"name":"Транспорт","kind":"expense","accent_color":"#ff8a3d"}]')
            return
        if "/api/v1/categories" in url and method == "GET":
            if "page=" in url and "page_size=" in url:
                route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
                return
            route.fulfill(status=200, content_type="application/json", body="[]")
            return
        if url.endswith("/api/v1/categories") and method == "POST":
            payload = request.post_data_json
            created_categories.append(payload)
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"id": len(created_categories), **payload}))
            return
        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/**", handle_request)
    page.add_init_script("""window.localStorage.setItem("access_token", "test-token");""")

    page.goto("http://127.0.0.1:8001/", wait_until="networkidle")
    page.locator("#mainNav button[data-section='categories']").click()
    page.get_by_role("button", name="+ Массовое добавление").click()
    page.locator("#batchCategoryInput").fill(
        "Расход;Такси;Транспорт\n"
        "Доход;Подработка;Неизвестная группа"
    )
    page.get_by_role("button", name="Проверить строки").click()
    page.get_by_role("button", name="Импортировать 2 строк").click()

    page.wait_for_timeout(300)

    assert len(created_categories) == 2
    assert created_categories[0]["kind"] == "expense"
    assert created_categories[0]["name"] == "Такси"
    assert created_categories[0]["group_id"] == 7
    assert created_categories[1]["kind"] == "income"
    assert created_categories[1]["name"] == "Подработка"
    assert created_categories[1]["group_id"] is None


@pytest.mark.e2e
def test_batch_category_groups_mode_accepts_trailing_semicolon(page):
    created_groups = []

    def handle_request(route):
        request = route.request
        url = request.url
        method = request.method

        if url.endswith("/api/v1/auth/public-config"):
            route.fulfill(status=200, content_type="application/json", body='{"telegram_bot_username":"FinanceWeaselBot","browser_login_available":true}')
            return
        if url.endswith("/api/v1/users/me"):
            route.fulfill(status=200, content_type="application/json", body='{"id":1,"display_name":"Admin","status":"approved","is_admin":true,"username":"owner_admin","telegram_id":"281896361"}')
            return
        if "/api/v1/preferences" in url:
            route.fulfill(status=200, content_type="application/json", body='{"data":{"ui":{}}}')
            return
        if "/api/v1/dashboard/summary" in url:
            route.fulfill(status=200, content_type="application/json", body='{"income_total":"0.00","expense_total":"0.00","balance":"0.00","debt_lend_total":"0.00","debt_borrow_total":"0.00","debt_net_total":"0.00"}')
            return
        if "/api/v1/dashboard/operations" in url or "/api/v1/dashboard/analytics" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if "/api/v1/operations?" in url or "/api/v1/debts" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if url.endswith("/api/v1/categories/groups") and method == "GET":
            route.fulfill(status=200, content_type="application/json", body="[]")
            return
        if url.endswith("/api/v1/categories/groups") and method == "POST":
            payload = request.post_data_json
            created_groups.append(payload)
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"id": len(created_groups), **payload}))
            return
        if "/api/v1/categories" in url and method == "GET":
            if "page=" in url and "page_size=" in url:
                route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
                return
            route.fulfill(status=200, content_type="application/json", body="[]")
            return
        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/**", handle_request)
    page.add_init_script("""window.localStorage.setItem("access_token", "test-token");""")

    page.goto("http://127.0.0.1:8001/", wait_until="networkidle")
    page.locator("#mainNav button[data-section='categories']").click()
    page.get_by_role("button", name="+ Массовое добавление").click()
    page.get_by_role("button", name="Группы").click()
    page.locator("#batchCategoryInput").fill(
        "Расход;Еда;\n"
        "Доход;Зарплата;"
    )
    page.get_by_role("button", name="Проверить строки").click()
    page.get_by_role("button", name="Импортировать 2 строк").click()

    page.wait_for_timeout(300)

    assert len(created_groups) == 2
    assert created_groups[0]["kind"] == "expense"
    assert created_groups[0]["name"] == "Еда"
    assert created_groups[1]["kind"] == "income"
    assert created_groups[1]["name"] == "Зарплата"


@pytest.mark.e2e
def test_batch_item_template_modal_imports_multiple_rows(page):
    created_templates = []

    def handle_request(route):
        request = route.request
        url = request.url
        method = request.method

        if url.endswith("/api/v1/auth/public-config"):
            route.fulfill(status=200, content_type="application/json", body='{"telegram_bot_username":"FinanceWeaselBot","browser_login_available":true}')
            return
        if url.endswith("/api/v1/users/me"):
            route.fulfill(status=200, content_type="application/json", body='{"id":1,"display_name":"Admin","status":"approved","is_admin":true,"username":"owner_admin","telegram_id":"281896361"}')
            return
        if "/api/v1/preferences" in url:
            route.fulfill(status=200, content_type="application/json", body='{"data":{"ui":{}}}')
            return
        if "/api/v1/dashboard/summary" in url:
            route.fulfill(status=200, content_type="application/json", body='{"income_total":"0.00","expense_total":"0.00","balance":"0.00","debt_lend_total":"0.00","debt_borrow_total":"0.00","debt_net_total":"0.00"}')
            return
        if "/api/v1/dashboard/operations" in url or "/api/v1/dashboard/analytics" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if "/api/v1/operations?" in url or "/api/v1/debts" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if "/api/v1/categories/groups" in url:
            route.fulfill(status=200, content_type="application/json", body="[]")
            return
        if "/api/v1/categories" in url and method == "GET":
            if "page=" in url and "page_size=" in url:
                route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
                return
            route.fulfill(status=200, content_type="application/json", body="[]")
            return
        if "/api/v1/operations/item-templates" in url and method == "GET":
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":100}')
            return
        if url.endswith("/api/v1/operations/item-templates") and method == "POST":
            payload = request.post_data_json
            created_templates.append(payload)
            route.fulfill(status=201, content_type="application/json", body=json.dumps({"id": len(created_templates), **payload}))
            return
        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/**", handle_request)
    page.add_init_script("""window.localStorage.setItem("access_token", "test-token");""")

    page.goto("http://127.0.0.1:8001/", wait_until="networkidle")
    page.get_by_role("button", name="Каталог позиций").click()
    page.get_by_role("button", name="+ Массовое добавление").click()
    page.locator("#batchItemTemplateInput").fill(
        "Евроопт;Сигареты Rothmans;9,40\n"
        "WB;USB кабель;"
    )
    page.get_by_role("button", name="Проверить строки").click()
    page.get_by_role("button", name="Импортировать 2 строк").click()

    page.wait_for_timeout(300)

    assert len(created_templates) == 2
    assert created_templates[0]["shop_name"] == "Евроопт"
    assert created_templates[0]["name"] == "Сигареты Rothmans"
    assert created_templates[0]["latest_unit_price"] == "9.40"
    assert created_templates[1]["shop_name"] == "WB"
    assert created_templates[1]["name"] == "USB кабель"
    assert created_templates[1]["latest_unit_price"] is None


@pytest.mark.e2e
def test_mobile_batch_category_modal_preview_stays_above_sticky_cta(page):
    def handle_request(route):
        request = route.request
        url = request.url
        method = request.method

        if url.endswith("/api/v1/auth/public-config"):
            route.fulfill(status=200, content_type="application/json", body='{"telegram_bot_username":"FinanceWeaselBot","browser_login_available":true}')
            return
        if url.endswith("/api/v1/users/me"):
            route.fulfill(status=200, content_type="application/json", body='{"id":1,"display_name":"Admin","status":"approved","is_admin":true,"username":"owner_admin","telegram_id":"281896361"}')
            return
        if "/api/v1/preferences" in url:
            route.fulfill(status=200, content_type="application/json", body='{"data":{"ui":{}}}')
            return
        if "/api/v1/dashboard/summary" in url:
            route.fulfill(status=200, content_type="application/json", body='{"income_total":"0.00","expense_total":"0.00","balance":"0.00","debt_lend_total":"0.00","debt_borrow_total":"0.00","debt_net_total":"0.00"}')
            return
        if "/api/v1/dashboard/operations" in url or "/api/v1/dashboard/analytics" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if "/api/v1/operations?" in url or "/api/v1/debts" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if url.endswith("/api/v1/categories/groups") and method == "GET":
            route.fulfill(status=200, content_type="application/json", body='[{"id":7,"name":"Транспорт","kind":"expense","accent_color":"#ff8a3d"}]')
            return
        if "/api/v1/categories" in url and method == "GET":
            if "page=" in url and "page_size=" in url:
                route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
                return
            route.fulfill(status=200, content_type="application/json", body="[]")
            return
        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/**", handle_request)
    page.add_init_script("""window.localStorage.setItem("access_token", "test-token");""")
    page.set_viewport_size({"width": 390, "height": 844})

    page.goto("http://127.0.0.1:8001/", wait_until="networkidle")
    page.click("#mobileNavToggleBtn")
    page.locator("#mainNav button[data-section='categories']").click()
    page.get_by_role("button", name="+ Массовое добавление").click()
    page.locator("#batchCategoryInput").fill(
        "Расход;Такси;Транспорт\n"
        "Доход;Подработка;Неизвестная группа"
    )
    page.get_by_role("button", name="Проверить строки").click()
    page.wait_for_selector("#batchCategoryPreview:not(.hidden)")
    page.evaluate(
        """
        () => {
          const modalCard = document.querySelector('#batchCategoryModal .modal-card');
          if (modalCard) {
            modalCard.scrollTop = modalCard.scrollHeight;
          }
        }
        """
    )
    page.wait_for_timeout(150)

    geometry = page.evaluate(
        """
        () => {
          const previewRow = document.querySelector('#batchCategoryPreviewBody tr:last-child');
          const previewPanel = document.querySelector('#batchCategoryPreview');
          const footer = document.querySelector('#batchCategoryModal .modal-footer');
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
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["previewPanelTop"] < geometry["footerTop"]
    assert geometry["previewRowTop"] < geometry["footerTop"]
    assert geometry["previewRowBottom"] <= geometry["footerTop"] + 2


@pytest.mark.e2e
def test_mobile_batch_item_template_modal_preview_stays_above_sticky_cta(page):
    def handle_request(route):
        request = route.request
        url = request.url
        method = request.method

        if url.endswith("/api/v1/auth/public-config"):
            route.fulfill(status=200, content_type="application/json", body='{"telegram_bot_username":"FinanceWeaselBot","browser_login_available":true}')
            return
        if url.endswith("/api/v1/users/me"):
            route.fulfill(status=200, content_type="application/json", body='{"id":1,"display_name":"Admin","status":"approved","is_admin":true,"username":"owner_admin","telegram_id":"281896361"}')
            return
        if "/api/v1/preferences" in url:
            route.fulfill(status=200, content_type="application/json", body='{"data":{"ui":{}}}')
            return
        if "/api/v1/dashboard/summary" in url:
            route.fulfill(status=200, content_type="application/json", body='{"income_total":"0.00","expense_total":"0.00","balance":"0.00","debt_lend_total":"0.00","debt_borrow_total":"0.00","debt_net_total":"0.00"}')
            return
        if "/api/v1/dashboard/operations" in url or "/api/v1/dashboard/analytics" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if "/api/v1/operations?" in url or "/api/v1/debts" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if "/api/v1/categories/groups" in url:
            route.fulfill(status=200, content_type="application/json", body="[]")
            return
        if "/api/v1/categories" in url and method == "GET":
            if "page=" in url and "page_size=" in url:
                route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
                return
            route.fulfill(status=200, content_type="application/json", body="[]")
            return
        if "/api/v1/operations/item-templates" in url and method == "GET":
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":100}')
            return
        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/**", handle_request)
    page.add_init_script("""window.localStorage.setItem("access_token", "test-token");""")
    page.set_viewport_size({"width": 390, "height": 844})

    page.goto("http://127.0.0.1:8001/", wait_until="networkidle")
    page.click("#mobileNavToggleBtn")
    page.get_by_role("button", name="Каталог позиций").click()
    page.get_by_role("button", name="+ Массовое добавление").click()
    page.locator("#batchItemTemplateInput").fill(
        "Евроопт;Сигареты Rothmans;9,40\n"
        "WB;USB кабель;"
    )
    page.get_by_role("button", name="Проверить строки").click()
    page.wait_for_selector("#batchItemTemplatePreview:not(.hidden)")
    page.evaluate(
        """
        () => {
          const modalCard = document.querySelector('#batchItemTemplateModal .modal-card');
          if (modalCard) {
            modalCard.scrollTop = modalCard.scrollHeight;
          }
        }
        """
    )
    page.wait_for_timeout(150)

    geometry = page.evaluate(
        """
        () => {
          const previewRow = document.querySelector('#batchItemTemplatePreviewBody tr:last-child');
          const previewPanel = document.querySelector('#batchItemTemplatePreview');
          const footer = document.querySelector('#batchItemTemplateModal .modal-footer');
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
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["previewPanelTop"] < geometry["footerTop"]
    assert geometry["previewRowTop"] < geometry["footerTop"]
    assert geometry["previewRowBottom"] <= geometry["footerTop"] + 2


@pytest.mark.e2e
def test_category_group_context_create_prefills_group_from_hover_action(page, static_server_url: str):
    created_groups = []

    def handle_request(route):
        request = route.request
        url = request.url
        method = request.method

        if url.endswith("/api/v1/auth/public-config"):
            route.fulfill(status=200, content_type="application/json", body='{"telegram_bot_username":"FinanceWeaselBot","browser_login_available":true}')
            return
        if url.endswith("/api/v1/users/me"):
            route.fulfill(status=200, content_type="application/json", body='{"id":1,"display_name":"Admin","status":"approved","is_admin":true,"username":"owner_admin","telegram_id":"281896361"}')
            return
        if "/api/v1/preferences" in url:
            if method == "PUT":
                route.fulfill(status=200, content_type="application/json", body=request.post_data or '{"data":{"ui":{}}}')
                return
            route.fulfill(status=200, content_type="application/json", body='{"data":{"ui":{}}}')
            return
        if "/api/v1/dashboard/summary" in url:
            route.fulfill(status=200, content_type="application/json", body='{"income_total":"0.00","expense_total":"0.00","balance":"0.00","debt_lend_total":"0.00","debt_borrow_total":"0.00","debt_net_total":"0.00"}')
            return
        if "/api/v1/dashboard/operations" in url or "/api/v1/dashboard/analytics" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if "/api/v1/operations" in url or "/api/v1/debts" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if url.endswith("/api/v1/categories/groups") and method == "GET":
            route.fulfill(status=200, content_type="application/json", body='[{"id":7,"name":"Еда","kind":"expense","accent_color":"#ff8a3d"}]')
            return
        if url.endswith("/api/v1/categories/groups") and method == "POST":
            created_groups.append(request.post_data_json)
            route.fulfill(status=200, content_type="application/json", body='{"id":8,"name":"Дом","kind":"income","accent_color":"#ff8a3d"}')
            return
        if "/api/v1/categories" in url and method == "GET":
            if "page=" in url and "page_size=" in url:
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body='{"items":[{"id":21,"name":"Снеки","icon":null,"kind":"expense","group_id":7,"group_name":"Еда","group_icon":null,"group_accent_color":"#ff8a3d","is_system":false}],"total":1,"page":1,"page_size":20}',
                )
                return
            route.fulfill(status=200, content_type="application/json", body='[{"id":21,"name":"Снеки","icon":null,"kind":"expense","group_id":7,"group_name":"Еда","group_icon":null,"group_accent_color":"#ff8a3d","is_system":false}]')
            return
        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/**", handle_request)
    page.add_init_script("""window.localStorage.setItem("access_token", "test-token");""")
    page.set_viewport_size({"width": 1280, "height": 850})

    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.locator("#mainNav button[data-section='categories']").click()
    page.wait_for_selector(".category-table-group-wrap", state="visible")
    page.wait_for_selector("tr.category-child-row:not(.hidden)", state="visible")
    page.wait_for_selector("button[data-create-category-group-id='7']", state="attached")
    page.locator(".category-table-group-wrap", has_text="Еда").hover()
    page.locator(".category-table-group-wrap", has_text="Еда").click(position={"x": 520, "y": 20})
    page.wait_for_function("() => document.querySelector('tr.category-child-row')?.classList.contains('hidden')")
    page.locator(".category-table-group-wrap", has_text="Еда").click(position={"x": 520, "y": 20})
    page.wait_for_selector("tr.category-child-row:not(.hidden)", state="visible")
    page.locator("button.category-context-create-btn[data-create-category-group-id='7']").click()

    page.wait_for_selector("#createCategoryModal:not(.hidden)")
    assert page.locator("#categoryGroup").input_value() == "7"
    assert page.locator("#categoryGroupSearch").input_value() == "Еда"
    assert "active" in page.locator("button[data-cat-create-kind='expense']").get_attribute("class")

    page.locator("#categoryGroupSearch").click()
    page.wait_for_timeout(100)
    page.wait_for_selector("#createCategoryGroupPickerBlock:not(.hidden)")
    assert page.locator("#createCategoryGroupPickerBlock").is_visible()
    page.locator("#categoryGroupAll button[data-group-id='7']").click()
    assert page.locator("#categoryGroupSearch").input_value() == "Еда"

    page.locator("#categoryIconToggle").click()
    page.wait_for_selector("#categoryIconPopover:not(.hidden)")
    assert page.locator("#categoryIconPopover .icon-option-group-title").count() >= 10
    assert page.locator('#categoryIconPopover button[data-icon="🚿"]').count() == 1
    assert page.locator('#categoryIconPopover button[data-icon="↩️"]').count() == 1
    assert page.locator('#categoryIconPopover button[data-icon="✂️"][aria-label="Барбер / стрижка"]').count() == 1
    assert page.locator('#categoryIconPopover button[data-icon="🎰"][aria-label="Ставки / азартные игры"]').count() == 1
    assert page.locator('#categoryIconPopover button[data-icon="🫖"]').count() == 0
    assert page.locator('#categoryIconPopover button[data-icon="🪴"]').count() == 0
    icon_picker_geometry = page.locator("#categoryIconPopover").evaluate(
        "node => ({ height: node.getBoundingClientRect().height, scrollHeight: node.scrollHeight })"
    )
    assert icon_picker_geometry["height"] <= 522
    assert icon_picker_geometry["scrollHeight"] > icon_picker_geometry["height"]
    page.screenshot(path="/tmp/finasist-category-icon-picker.png", full_page=True)
    page.locator('#categoryIconPopover button[data-icon="🚿"]').click()
    assert page.locator("#categoryIcon").input_value() == "🚿"
    assert "🚿" in page.locator("#categoryIconToggle").inner_text()

    geometry = page.evaluate(
        """
        () => {
          const row = document.querySelector('.category-table-group-wrap');
          const name = row?.querySelector('.item-catalog-group-name');
          const create = row?.querySelector('.category-context-create-btn');
          if (!row || !name || !create) {
            return null;
          }
          const rowRect = row.getBoundingClientRect();
          const nameRect = name.getBoundingClientRect();
          const createRect = create.getBoundingClientRect();
          return {
            nameRight: nameRect.right,
            createLeft: createRect.left,
            createFromRowLeft: createRect.left - rowRect.left,
          };
        }
        """
    )
    assert geometry is not None
    assert 0 <= geometry["createLeft"] - geometry["nameRight"] <= 24
    assert geometry["createFromRowLeft"] < 180

    page.set_viewport_size({"width": 390, "height": 844})
    page.locator("#categoryIconToggle").click()
    page.wait_for_selector("#categoryIconPopover:not(.hidden)")
    mobile_icon_picker_geometry = page.locator("#categoryIconPopover").evaluate(
        """
        node => {
          const rect = node.getBoundingClientRect();
          return {
            left: rect.left,
            right: rect.right,
            bodyClientWidth: document.documentElement.clientWidth,
            bodyScrollWidth: document.documentElement.scrollWidth,
          };
        }
        """
    )
    assert mobile_icon_picker_geometry["left"] >= 0
    assert mobile_icon_picker_geometry["right"] <= 390
    assert mobile_icon_picker_geometry["bodyScrollWidth"] <= mobile_icon_picker_geometry["bodyClientWidth"] + 1
    page.screenshot(path="/tmp/finasist-category-icon-picker-mobile.png", full_page=True)
    page.locator('#categoryIconPopover button[data-icon=""]').click()
    page.wait_for_function("() => document.querySelector('#categoryIconPopover')?.classList.contains('hidden')")
    page.set_viewport_size({"width": 1280, "height": 850})

    page.locator("#closeCreateCategoryModalBtn").click()
    page.wait_for_function("() => document.querySelector('#createCategoryModal')?.classList.contains('hidden')")

    page.locator("#addGroupCta").click()
    page.wait_for_selector("#createGroupModal:not(.hidden)")
    page.locator("button[data-group-create-kind='income']").click()
    assert page.locator("#groupKind").input_value() == "income"
    page.locator("#groupName").fill("Дом")
    page.locator("#submitCreateGroupBtn").click()
    page.wait_for_function("() => document.querySelector('#createGroupModal')?.classList.contains('hidden')")
    assert created_groups == [{"name": "Дом", "kind": "income", "accent_color": "#ff8a3d"}]


@pytest.mark.e2e
def test_item_source_context_create_prefills_source_from_hover_action(page, static_server_url: str):
    def handle_request(route):
        request = route.request
        url = request.url
        method = request.method

        if url.endswith("/api/v1/auth/public-config"):
            route.fulfill(status=200, content_type="application/json", body='{"telegram_bot_username":"FinanceWeaselBot","browser_login_available":true}')
            return
        if url.endswith("/api/v1/users/me"):
            route.fulfill(status=200, content_type="application/json", body='{"id":1,"display_name":"Admin","status":"approved","is_admin":true,"username":"owner_admin","telegram_id":"281896361"}')
            return
        if "/api/v1/preferences" in url:
            route.fulfill(status=200, content_type="application/json", body='{"data":{"ui":{},"item_catalog_sources":["Евроопт"]}}')
            return
        if "/api/v1/dashboard/summary" in url:
            route.fulfill(status=200, content_type="application/json", body='{"income_total":"0.00","expense_total":"0.00","balance":"0.00","debt_lend_total":"0.00","debt_borrow_total":"0.00","debt_net_total":"0.00"}')
            return
        if "/api/v1/dashboard/operations" in url or "/api/v1/dashboard/analytics" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        if "/api/v1/operations/item-templates" in url and method == "GET":
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"items":[{"id":31,"name":"Молоко","shop_name":"Евроопт","latest_unit_price":"3.20","latest_price_date":"2026-06-01","use_count":2}],"total":1,"page":1,"page_size":100}',
            )
            return
        if "/api/v1/categories/groups" in url:
            route.fulfill(status=200, content_type="application/json", body="[]")
            return
        if "/api/v1/categories" in url and method == "GET":
            if "page=" in url and "page_size=" in url:
                route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
                return
            route.fulfill(status=200, content_type="application/json", body="[]")
            return
        if "/api/v1/operations" in url or "/api/v1/debts" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return
        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/**", handle_request)
    page.add_init_script("""window.localStorage.setItem("access_token", "test-token");""")
    page.set_viewport_size({"width": 1280, "height": 850})

    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.get_by_role("button", name="Каталог позиций").click()
    page.wait_for_selector(".item-catalog-source-wrap", state="visible")
    page.wait_for_selector("tr.item-catalog-item-row", state="visible")
    page.wait_for_selector("button[data-create-item-template-source-name='Евроопт']", state="attached")
    page.locator(".item-catalog-source-wrap", has_text="Евроопт").hover()
    page.locator(".item-catalog-source-wrap", has_text="Евроопт").click(position={"x": 520, "y": 34})
    page.wait_for_function("() => document.querySelector('tr.item-catalog-item-row')?.classList.contains('hidden')")
    page.locator(".item-catalog-source-wrap", has_text="Евроопт").click(position={"x": 520, "y": 34})
    page.wait_for_selector("tr.item-catalog-item-row:not(.hidden)", state="visible")

    geometry = page.evaluate(
        """
        () => {
          const row = document.querySelector('.item-catalog-source-wrap');
          const name = row?.querySelector('.item-catalog-group-name');
          const create = row?.querySelector('.item-source-context-create-btn');
          if (!row || !name || !create) {
            return null;
          }
          const rowRect = row.getBoundingClientRect();
          const nameRect = name.getBoundingClientRect();
          const createRect = create.getBoundingClientRect();
          return {
            nameRight: nameRect.right,
            createLeft: createRect.left,
            createFromRowLeft: createRect.left - rowRect.left,
          };
        }
        """
    )
    assert geometry is not None
    assert 0 <= geometry["createLeft"] - geometry["nameRight"] <= 24
    assert geometry["createFromRowLeft"] < 220

    page.locator("button.item-source-context-create-btn[data-create-item-template-source-name='Евроопт']").click()

    page.wait_for_selector("#itemTemplateModal:not(.hidden)")
    assert page.locator("#itemTemplateSource").input_value() == "Евроопт"
    assert page.locator("#itemTemplateSourceSearch").input_value() == "Евроопт"
    assert page.evaluate("() => document.activeElement?.id") == "itemTemplateName"
