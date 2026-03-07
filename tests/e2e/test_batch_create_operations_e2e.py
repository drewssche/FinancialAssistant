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
                    f'"operation_date":"{payload["operation_date"]}","category_id":null,'
                    f'"note":"{payload.get("note", "")}","receipt_items":[],"receipt_total":null,"receipt_discrepancy":null}}'
                ),
            )
            return

        if "/api/v1/categories" in url:
            route.fulfill(status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}')
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
        "expense;150.50;2026-03-04;Такси\n"
        "income;1000;2026-03-05;Зарплата"
    )
    page.get_by_role("button", name="Добавить пакет").click()

    page.wait_for_timeout(300)

    assert len(operations_created) == 2
    assert operations_created[0]["kind"] == "expense"
    assert operations_created[0]["amount"] == "150.50"
    assert operations_created[0]["operation_date"] == "2026-03-04"
    assert operations_created[0]["note"] == "Такси"
    assert operations_created[1]["kind"] == "income"
    assert operations_created[1]["amount"] == "1000"
    assert operations_created[1]["operation_date"] == "2026-03-05"
    assert operations_created[1]["note"] == "Зарплата"
