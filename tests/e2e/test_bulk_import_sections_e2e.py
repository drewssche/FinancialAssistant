import json

import pytest


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
    page.get_by_role("button", name="Категории").click()
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
    page.get_by_role("button", name="Категории").click()
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
    page.get_by_role("button", name="Категории").click()
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
    page.get_by_role("button", name="Категории").click()
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
