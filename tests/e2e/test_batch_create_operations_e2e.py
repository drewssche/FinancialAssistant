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
                    body='{"items":[{"id":10,"name":"Такси","icon":null,"kind":"expense","group_id":null,"group_name":null,"group_icon":null,"group_accent_color":null,"is_system":false},{"id":11,"name":"Зарплата","icon":null,"kind":"income","group_id":null,"group_name":null,"group_icon":null,"group_accent_color":null,"is_system":false}],"total":2,"page":1,"page_size":20}',
                )
                return
            route.fulfill(
                status=200,
                content_type="application/json",
                body='[{"id":10,"name":"Такси","icon":null,"kind":"expense","group_id":null,"group_name":null,"group_icon":null,"group_accent_color":null,"is_system":false},{"id":11,"name":"Зарплата","icon":null,"kind":"income","group_id":null,"group_name":null,"group_icon":null,"group_accent_color":null,"is_system":false}]',
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
        "2026-03-04;Расход;Такси;150,50;Поездка\n"
        "2026-03-05;Доход;Зарплата;1000;"
    )
    page.get_by_role("button", name="Проверить строки").click()
    page.get_by_role("button", name="Импортировать 2 строк").click()

    page.wait_for_timeout(300)

    assert len(operations_created) == 2
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
