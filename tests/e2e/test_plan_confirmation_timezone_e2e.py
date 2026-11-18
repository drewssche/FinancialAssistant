from datetime import datetime, timezone
from urllib.parse import urlsplit
from unittest.mock import Mock

import pytest
from playwright.sync_api import expect

from tests.api.test_operations_api import _client_lifecycle
from tests.e2e.test_plans_ui_e2e import (
    _login_and_open_plans, page_with_plans_api_mock, static_server_url,
)


@pytest.fixture
def api():
    yield from _client_lifecycle()


@pytest.mark.e2e
@pytest.mark.browser_context_args(timezone_id="Europe/Minsk")
def test_early_confirmation_after_minsk_midnight(page_with_plans_api_mock, static_server_url, api, monkeypatch):
    page, state = page_with_plans_api_mock
    midnight = datetime.fromisoformat("2026-11-15T00:00:01+03:00")
    page.clock.set_fixed_time(midnight)
    clock = Mock(wraps=datetime)
    clock.now.return_value = midnight.astimezone(timezone.utc)
    monkeypatch.setattr("app.services.plan_service.datetime", clock)
    state["preferences"]["data"]["ui"].update(timezone="auto", browser_timezone="Europe/Minsk")
    assert api.put("/api/v1/preferences", json=state["preferences"]).status_code == 200
    for fields in [
        {"kind": "expense", "amount": "22.41", "currency": "USD", "fx_rate_source": "manual",
         "fx_manual_rate": "3.0", "note": "Оплата на месяц", "tags": ["работа"],
         "recurrence_enabled": True, "recurrence_frequency": "monthly",
         "receipt_items": [{"name": "Подписка", "unit_price": "22.41", "tags": ["сервис"]}]},
        {"kind": "income", "amount": "100", "note": "Гонорар"},
    ]:
        plan = api.post("/api/v1/plans", json={"scheduled_date": "2026-11-20", **fields})
        assert plan.status_code == 201, plan.text

    # Exercise the browser button against the real plans API and its isolated database.
    def plans_api(route, request):
        url = urlsplit(request.url)
        response = api.request(request.method, url.path, params=url.query)
        route.fulfill(status=response.status_code, content_type="application/json", body=response.content)

    page.route(lambda url: urlsplit(url).path.startswith("/api/v1/plans"), plans_api)
    page.route(lambda url: urlsplit(url).path.startswith("/api/v1/operations/") and
               urlsplit(url).path.rsplit("/", 1)[-1].isdigit(), plans_api)
    _login_and_open_plans(page, static_server_url)
    for title, kind, note in [("Подписка", "расход", "Оплата на месяц"), ("Гонорар", "доход", "Гонорар")]:
        card = page.locator("#plansList article").filter(has=page.get_by_role("heading", name=title, exact=True))
        expect(card).to_contain_text("20.11.2026")
        with page.expect_response(lambda response: response.url.endswith("/confirm")) as result:
            card.get_by_role("button", name=f"Записать {kind}").press("Enter")
        confirmation = result.value.json()
        op = confirmation["operation"]
        assert op["operation_date"] == "2026-11-15"
        if kind == "расход":
            assert op["currency"] == "USD" and op["original_amount"] == "22.41" and op["amount"] == "67.23"
            assert op["tags"] == ["работа"] and op["receipt_items"][0]["tags"] == ["сервис"]
            assert confirmation["plan"]["scheduled_date"] == "2026-12-20"
        toast = page.locator(".toast-success").filter(has_text=f"{kind.capitalize()} записан за 15.11.2026 · {title}")
        with page.expect_response(lambda response: urlsplit(response.url).path == f"/api/v1/operations/{op['id']}"):
            toast.get_by_role("button", name="Открыть операцию").click()
        expect(page.locator("#editDate")).to_have_value("2026-11-15")
        expect(page.locator("#editNote")).to_have_value(note)
        page.click("#closeEditModalBtn")
    page.click('button[data-plan-tab="history"]')
    expect(page.locator(".plan-history-card").get_by_text("Дата операции · 15.11.2026")).to_have_count(2)
    assert len(api.get("/api/v1/operations").json()["items"]) == 2
