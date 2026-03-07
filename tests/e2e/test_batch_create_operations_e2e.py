import pytest


@pytest.mark.e2e
def test_batch_create_modal_submits_multiple_operations(page):
    operations_created = []

    def handle_request(route):
        request = route.request
        url = request.url
        method = request.method

        if url.endswith("/api/v1/auth/public-config"):
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"telegram_bot_username":"FinanceWeaselBot","browser_login_available":true}',
            )
            return

        if url.endswith("/api/v1/users/me"):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=(
                    '{"id":1,"display_name":"Admin","status":"approved","is_admin":true,'
                    '"username":"owner_admin","telegram_id":"281896361"}'
                ),
            )
            return

        if "/api/v1/dashboard/summary" in url:
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"income_total":"0.00","expense_total":"0.00","balance":"0.00","debt_lend_total":"0.00","debt_borrow_total":"0.00","debt_net_total":"0.00"}',
            )
            return

        if "/api/v1/dashboard/operations" in url:
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"items":[],"total":0,"page":1,"page_size":20}',
            )
            return

        if "/api/v1/dashboard/analytics" in url:
            route.fulfill(status=200, content_type="application/json", body='{"points":[],"summary":{}}')
            return

        if "/api/v1/operations?" in url and method == "GET":
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"items":[],"total":0,"page":1,"page_size":20}',
            )
            return

        if url.endswith("/api/v1/operations") and method == "POST":
            payload = request.post_data_json
            operations_created.append(payload)
            idx = len(operations_created)
            route.fulfill(
                status=201,
                content_type="application/json",
                body=(
                    f'{{"id":{idx},"kind":"{payload["kind"]}","amount":"{payload["amount"]}",'
                    f'"operation_date":"{payload["operation_date"]}","category_id":{payload["category_id"]},'
                    f'"note":"{payload.get("note", "")}","receipt_items":[],"receipt_total":null,"receipt_discrepancy":null}}'
                ),
            )
            return

        if "/api/v1/categories" in url and method == "GET":
            if "page=" in url and "page_size=" in url:
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body='{"items":[{"id":10,"name":"Такси","icon":null,"kind":"expense","group_id":null,"group_name":null,"group_icon":null,"group_accent_color":null,"is_system":false},{"id":11,"name":"Зарплата","icon":null,"kind":"income","group_id":5,"group_name":"Работа","group_icon":null,"group_accent_color":"#49be78","is_system":false},{"id":12,"name":"Снеки/сладости/фастфуд","icon":null,"kind":"expense","group_id":6,"group_name":"Еда","group_icon":null,"group_accent_color":"#ff8a3d","is_system":false}],"total":3,"page":1,"page_size":20}',
                )
                return
            route.fulfill(
                status=200,
                content_type="application/json",
                body='[{"id":10,"name":"Такси","icon":null,"kind":"expense","group_id":null,"group_name":null,"group_icon":null,"group_accent_color":null,"is_system":false},{"id":11,"name":"Зарплата","icon":null,"kind":"income","group_id":5,"group_name":"Работа","group_icon":null,"group_accent_color":"#49be78","is_system":false},{"id":12,"name":"Снеки/сладости/фастфуд","icon":null,"kind":"expense","group_id":6,"group_name":"Еда","group_icon":null,"group_accent_color":"#ff8a3d","is_system":false}]',
            )
            return

        if "/api/v1/debts" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0}')
            return

        if "/api/v1/preferences" in url:
            route.fulfill(status=200, content_type="application/json", body='{"data":{"ui":{}}}')
            return

        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/**", handle_request)
    page.add_init_script(
        """
        window.localStorage.setItem("access_token", "test-token");
        """
    )

    page.goto("http://127.0.0.1:8001/", wait_until="networkidle")
    page.get_by_role("button", name="+ Массовое добавление").click()
    page.locator("#batchCreateInput").fill(
        "04.03.2026;Расход;;Такси;150,50;Поездка\n"
        "05.03.2026;Доход;Работа;Зарплата;1000;\n"
        "06.03.2026;Расход;;;50;Без категории\n"
        "07.03.2026;Расход;Еда;Снеки/сладости/фастфуд;4,28"
    )
    page.get_by_role("button", name="Проверить строки").click()
    page.get_by_role("button", name="Импортировать 4 строк").click()

    page.wait_for_timeout(300)

    assert len(operations_created) == 4
    assert operations_created[0]["kind"] == "expense"
    assert operations_created[0]["amount"] == "150.50"
    assert operations_created[0]["operation_date"] == "2026-03-04"
    assert operations_created[0]["category_id"] == 10
    assert operations_created[0]["note"] == "Поездка"
    assert operations_created[1]["kind"] == "income"
    assert operations_created[1]["amount"] == "1000.00"
    assert operations_created[1]["operation_date"] == "2026-03-05"
    assert operations_created[1]["category_id"] == 11
    assert operations_created[1]["note"] == ""
    assert operations_created[2]["kind"] == "expense"
    assert operations_created[2]["amount"] == "50.00"
    assert operations_created[2]["operation_date"] == "2026-03-06"
    assert operations_created[2]["category_id"] is None
    assert operations_created[2]["note"] == "Без категории"
    assert operations_created[3]["kind"] == "expense"
    assert operations_created[3]["amount"] == "4.28"
    assert operations_created[3]["operation_date"] == "2026-03-07"
    assert operations_created[3]["category_id"] == 12
    assert operations_created[3]["note"] == ""


@pytest.mark.e2e
def test_create_debt_modal_accepts_display_date_format(page):
    debt_payloads = []

    def handle_request(route):
        request = route.request
        url = request.url
        method = request.method

        if url.endswith("/api/v1/auth/public-config"):
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"telegram_bot_username":"FinanceWeaselBot","browser_login_available":true}',
            )
            return

        if url.endswith("/api/v1/users/me"):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=(
                    '{"id":1,"display_name":"Admin","status":"approved","is_admin":true,'
                    '"username":"owner_admin","telegram_id":"281896361"}'
                ),
            )
            return

        if "/api/v1/dashboard/summary" in url:
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"income_total":"0.00","expense_total":"0.00","balance":"0.00","debt_lend_total":"0.00","debt_borrow_total":"0.00","debt_net_total":"0.00"}',
            )
            return

        if "/api/v1/dashboard/operations" in url or "/api/v1/dashboard/analytics" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return

        if "/api/v1/operations?" in url and method == "GET":
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
            return

        if "/api/v1/categories" in url and method == "GET":
            if "page=" in url and "page_size=" in url:
                route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
                return
            route.fulfill(status=200, content_type="application/json", body="[]")
            return

        if url.endswith("/api/v1/debts") and method == "POST":
            payload = request.post_data_json
            debt_payloads.append(payload)
            route.fulfill(status=201, content_type="application/json", body='{"id":77,"counterparty":"Alex","direction":"lend","principal":"120.00","start_date":"2026-03-07","due_date":"2026-03-20","note":"Тест"}')
            return

        if "/api/v1/debts" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0}')
            return

        if "/api/v1/preferences" in url:
            route.fulfill(status=200, content_type="application/json", body='{"data":{"ui":{}}}')
            return

        route.fulfill(status=200, content_type="application/json", body="{}")

    page.route("**/api/**", handle_request)
    page.add_init_script("""window.localStorage.setItem("access_token", "test-token");""")

    page.goto("http://127.0.0.1:8001/", wait_until="networkidle")
    page.evaluate("window.App.actions.openCreateModal()")
    page.locator("#createModal").wait_for(state="visible")
    page.locator('#createModal #createEntryModeSwitch button[data-entry-mode="debt"]').click()
    page.fill("#debtStartDate", "07.03.2026")
    page.fill("#debtDueDate", "20.03.2026")
    page.fill("#debtCounterparty", "Alex")
    page.fill("#debtPrincipal", "120")
    page.fill("#debtNote", "Тест")
    page.get_by_role("button", name="Создать долг").click()

    page.wait_for_timeout(300)

    assert len(debt_payloads) == 1
    assert debt_payloads[0]["start_date"] == "2026-03-07"
    assert debt_payloads[0]["due_date"] == "2026-03-20"
