import pytest

from tests.e2e import test_directory_actions_e2e as directory_actions

static_server_url = directory_actions.static_server_url


@pytest.mark.e2e
def test_create_debt_modal_submits_native_date_values(page, static_server_url):
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

    page.goto(f"{static_server_url}/static/index.html", wait_until="networkidle")
    page.evaluate("window.App.actions.openCreateModal()")
    page.locator("#createModal").wait_for(state="visible")
    page.locator('#createModal #createEntryModeSwitch button[data-entry-mode="debt"]').click()
    page.fill("#debtStartDate", "2026-03-07")
    page.fill("#debtDueDate", "2026-03-20")
    page.fill("#debtCounterparty", "Alex")
    page.fill("#debtPrincipal", "120")
    page.fill("#debtNote", "Тест")
    page.get_by_role("button", name="Создать долг").click()

    page.wait_for_timeout(300)

    assert len(debt_payloads) == 1
    assert debt_payloads[0]["start_date"] == "2026-03-07"
    assert debt_payloads[0]["due_date"] == "2026-03-20"
