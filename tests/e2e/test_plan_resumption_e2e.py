from __future__ import annotations

import json
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect

from tests.e2e import test_plans_ui_e2e as plans_ui
from tests.e2e.test_plans_ui_e2e import _json_response, _login_and_open_plans, _make_plan_item

page_with_plans_api_mock = plans_ui.page_with_plans_api_mock
static_server_url = plans_ui.static_server_url


@pytest.fixture
def completed_plan_ui(page_with_plans_api_mock):
    page, state = page_with_plans_api_mock
    plan = {"id": 12, "kind": "expense", "amount": "2.99", "scheduled_date": "2026-08-28",
            "status": "confirmed", "note": "Подписка", "confirmed_operation_id": 3203, "confirm_count": 1}
    state["plans"] = [plan]
    state["history"] = [{"id": 50, "plan_id": 12, "operation_id": 3203, "event_type": "confirmed",
                         "kind": "expense", "amount": "2.99", "effective_date": "2026-08-28",
                         "category_name": "Подписки", "created_at": "2026-08-28T12:16:55Z"}]
    state["preview_requests"] = []
    state["updates"] = []

    def handler(route, request):
        path = urlparse(request.url).path
        if path == "/api/v1/plans/12/resume-preview":
            payload = json.loads(request.post_data)
            state["preview_requests"].append(payload)
            if state.get("preview_error"):
                return _json_response(route, {"detail": state["preview_error"]}, status=400)
            return _json_response(route, {"scheduled_date": payload.get("scheduled_date") or "2026-09-28"})
        if path == "/api/v1/plans/12":
            if request.method == "PATCH":
                payload = json.loads(request.post_data)
                state["updates"].append(payload)
                plan.update(payload)
                if payload.get("resume"):
                    plan["status"] = "upcoming"
            return _json_response(route, _make_plan_item(plan))
        if path == "/api/v1/operations/money-flow":
            return _json_response(route, {"items": [{"id": "operation:3203", "source_kind": "operation",
                "source_id": 3203, "source_plan_id": 12, "flow_direction": "outflow", "event_date": "2026-08-28",
                "amount": "2.99", "original_amount": "2.99", "currency": "BYN", "base_currency": "BYN",
                "title": "Подписки"}], "total": 1, "page": 1, "page_size": 20})
        return route.fallback()

    page.route("**/api/v1/**", handler)
    return page, state


def open_history_plan(page):
    page.click('[data-plan-tab="history"]')
    page.locator('[data-open-plan-id="12"]').click()
    expect(page.locator("#createTitle")).to_have_text("Редактировать план")
    expect(page.locator("#planEditorStatus")).to_have_text("План #12 · Завершён")


@pytest.mark.e2e
@pytest.mark.parametrize("width", [320, 1280])
def test_completed_plan_opens_from_history_and_resumes(static_server_url, completed_plan_ui, width):
    page, state = completed_plan_ui
    _login_and_open_plans(page, static_server_url)
    page.set_viewport_size({"width": width, "height": 900})
    open_history_plan(page)
    expect(page.locator("#planLinkedOperation")).to_have_text("Операция #3203")
    activity_before = page.evaluate("window.App.state.lastActivityMutationAt")
    page.click('[data-plan-schedule-mode="recurring"]')
    expect(page.locator("#planResumeEnabled")).to_be_checked()
    expect(page.locator("#planResumeDate")).to_have_value("2026-09-28")
    expect(page.locator("#submitCreateOperationBtn")).to_have_text("Сохранить и возобновить")
    expect(page.locator("#submitCreateOperationBtn")).to_be_enabled()
    assert page.evaluate("window.App.state.lastActivityMutationAt") == activity_before
    page.screenshot(path=f"/private/tmp/financialassistant-plan-resume-{width}.png")
    page.locator("#planResumeDate").fill("2026-10-05")
    page.locator("#planResumeDate").dispatch_event("change")
    expect(page.locator("#planResumeHint")).to_contain_text("05.10.2026")
    page.click("#submitCreateOperationBtn")
    expect(page.locator("#planEditorStatus")).to_have_text("План #12 · Активен")
    expect(page.locator("#submitCreateOperationBtn")).to_have_text("Сохранить план")
    assert state["updates"][-1]["resume"] is True
    assert state["updates"][-1]["scheduled_date"] == "2026-10-05"
    page.click("#planShowInList")
    expect(page.locator('[data-plan-tab="recurring"]')).to_have_class("segmented-btn active")
    expect(page.locator('[data-plan-card-edit-id="12"]')).to_be_visible()
    assert state["history"][0]["amount"] == "2.99"
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


@pytest.mark.e2e
def test_operation_source_chip_opens_completed_plan_directly(static_server_url, completed_plan_ui):
    page, state = completed_plan_ui
    _login_and_open_plans(page, static_server_url)
    page.click('button[data-section="operations"]')
    page.locator('button[data-open-source-kind="plan"][data-open-source-id="12"]').click()
    expect(page.locator("#planEditorStatus")).to_have_text("План #12 · Завершён")
    expect(page.locator("#activityModal")).to_be_hidden()
    page.locator("#opNote").fill("Изменённый комментарий")
    page.click("#submitCreateOperationBtn")
    expect(page.locator("#planEditorStatus")).to_have_text("План #12 · Завершён")
    assert not state["updates"][-1].get("resume")
    assert state["plans"][0]["status"] == "confirmed"


@pytest.mark.e2e
def test_resume_preview_error_prevents_save_and_toggle_off_cancels_resume(static_server_url, completed_plan_ui):
    page, state = completed_plan_ui
    state["preview_error"] = "Дата окончания повторения раньше следующего платежа"
    _login_and_open_plans(page, static_server_url)
    open_history_plan(page)
    page.click('[data-plan-schedule-mode="recurring"]')
    expect(page.locator("#planResumeHint")).to_contain_text(state["preview_error"])
    page.click("#submitCreateOperationBtn")
    assert state["updates"] == []
    page.click('[data-plan-month-end="on"]')
    page.click('[data-plan-schedule-mode="oneoff"]')
    expect(page.locator("#planResumeFields")).to_be_hidden()
    expect(page.locator("#submitCreateOperationBtn")).to_have_text("Сохранить план")
    page.click("#submitCreateOperationBtn")
    assert not state["updates"][-1].get("resume")
    assert state["updates"][-1]["scheduled_date"] == "2026-08-28"


@pytest.mark.e2e
def test_outdated_preview_cannot_overwrite_latest_schedule_or_new_form(static_server_url, completed_plan_ui):
    page, state = completed_plan_ui
    _login_and_open_plans(page, static_server_url)
    open_history_plan(page)
    page.evaluate("""() => {
      const original = window.App.core.requestJson;
      window.resumePreviews = [];
      window.App.core.requestJson = (url, options) => url.endsWith('/resume-preview')
        ? new Promise(resolve => window.resumePreviews.push(resolve)) : original(url, options);
    }""")
    page.click('[data-plan-schedule-mode="recurring"]')
    page.locator("#planRecurrenceFrequency").select_option("yearly")
    page.wait_for_function("window.resumePreviews.length === 2")
    page.evaluate("window.resumePreviews[1]({scheduled_date: '2027-08-28'})")
    expect(page.locator("#planResumeDate")).to_have_value("2027-08-28")
    page.evaluate("window.resumePreviews[0]({scheduled_date: '2026-09-28'})")
    expect(page.locator("#planResumeDate")).to_have_value("2027-08-28")
    page.locator("#planRecurrenceInterval").fill("2")
    page.wait_for_function("window.resumePreviews.length === 3")
    page.evaluate("window.App.getRuntimeModule('operation-modal').closeCreateModal()")
    page.click("#addPlanCta")
    page.evaluate("window.resumePreviews[2]({scheduled_date: '2028-08-28'})")
    expect(page.locator("#createTitle")).to_have_text("Новый план")
    expect(page.locator("#planResumeControls")).to_be_hidden()
    expect(page.locator("#submitCreateOperationBtn")).to_be_enabled()
    assert state["updates"] == []


@pytest.mark.e2e
def test_ended_recurring_plan_requires_explicit_resumption(static_server_url, completed_plan_ui):
    page, state = completed_plan_ui
    state["plans"][0].update(recurrence_enabled=True, recurrence_frequency="monthly", recurrence_end_date="2026-08-28")
    _login_and_open_plans(page, static_server_url)
    open_history_plan(page)
    expect(page.locator("#planResumeEnabled")).not_to_be_checked()
    page.locator("#opNote").fill("Изменение завершённого расписания")
    page.click("#submitCreateOperationBtn")
    assert not state["updates"][-1].get("resume")
    page.locator("#planRecurrenceEndDate").fill("")
    page.locator("#planResumeEnabled").check()
    expect(page.locator("#planResumeDate")).to_have_value("2026-09-28")
    page.click("#submitCreateOperationBtn")
    expect(page.locator("#planEditorStatus")).to_have_text("План #12 · Активен")
    assert state["updates"][-1]["resume"] is True
    assert state["updates"][-1]["recurrence_end_date"] is None


@pytest.mark.e2e
def test_save_response_does_not_replace_new_plan_form(static_server_url, completed_plan_ui):
    page, state = completed_plan_ui
    _login_and_open_plans(page, static_server_url)
    open_history_plan(page)
    page.evaluate("""() => {
      const original = window.App.core.requestJson;
      window.App.core.requestJson = (url, options) => url === '/api/v1/plans/12' && options?.method === 'PATCH'
        ? new Promise(resolve => { window.finishPlanSave = resolve; }) : original(url, options);
    }""")
    page.click("#submitCreateOperationBtn")
    page.wait_for_function("typeof window.finishPlanSave === 'function'")
    page.evaluate("window.App.getRuntimeModule('operation-modal').closeCreateModal()")
    page.click("#addPlanCta")
    page.locator("#opNote").fill("Новый несохранённый план")
    page.evaluate("window.finishPlanSave({id: 12, kind: 'expense', original_amount: '2.99', status: 'confirmed', scheduled_date: '2026-08-28'})")
    expect(page.locator("#submitCreateOperationBtn")).to_be_enabled()
    expect(page.locator("#createTitle")).to_have_text("Новый план")
    expect(page.locator("#opNote")).to_have_value("Новый несохранённый план")
    expect(page.locator("#submitCreateOperationBtn")).to_have_text("Создать план")
