from datetime import datetime, timezone
from urllib.parse import urlsplit
from unittest.mock import Mock

import pytest

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
    plan = api.post("/api/v1/plans", json={
        "kind": "expense", "amount": "22.41", "scheduled_date": "2026-11-20", "note": "Футболка",
    })
    assert plan.status_code == 201

    # Exercise the browser button against the real plans API and its isolated database.
    def plans_api(route, request):
        url = urlsplit(request.url)
        response = api.request(request.method, url.path, params=url.query)
        route.fulfill(status=response.status_code, content_type="application/json", body=response.content)

    page.route(lambda url: urlsplit(url).path.startswith("/api/v1/plans"), plans_api)
    _login_and_open_plans(page, static_server_url)
    with page.expect_response(lambda response: response.url.endswith("/confirm")) as result:
        page.locator('#plansList button[data-plan-action="confirm"]').click()
    assert result.value.json()["operation"]["operation_date"] == "2026-11-15"
    page.click('button[data-plan-tab="history"]')
    page.locator(".plan-history-card").get_by_text("15.11.2026", exact=False).first.wait_for()
    assert api.get("/api/v1/operations").json()["items"][0]["operation_date"] == "2026-11-15"
