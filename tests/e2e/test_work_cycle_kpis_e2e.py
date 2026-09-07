import json
from datetime import datetime, timezone
from urllib.parse import urlparse

import pytest

from tests.e2e.test_receipt_picker_store_scope_e2e import (
    _login,
    page_with_receipt_api_mock as page_with_receipt_api_mock,
    static_server_url as static_server_url,
)

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect


@pytest.fixture
def work_page(request):
    page = request.getfixturevalue("page_with_receipt_api_mock")
    url = request.getfixturevalue("static_server_url")
    page.clock.install(time=datetime(2026, 9, 7, 13, 30, tzinfo=timezone.utc))
    advance = {"operation_id": 701, "operation_date": "2026-08-20", "amount": "1420.00", "currency": "BYN", "base_amount": "1420.00", "base_currency": "BYN", "source": "manual"}
    salary = {"operation_id": 702, "operation_date": "2026-09-04", "amount": "2854.78", "currency": "BYN", "base_amount": "2854.78", "base_currency": "BYN", "source": "category_match"}
    cycle = {
        "reference_year": 2026, "reference_month": 8, "label": "Зарплата за август 2026 г.",
        "window_from_exclusive": "2026-08-05", "window_to_inclusive": "2026-09-04", "status": "actual",
        "components": [
            {"role": "advance", "label": "Аванс", "nominal_date": "2026-08-20", "effective_date": "2026-08-20", "status": "actual", "actual_operations": [advance], "actual_totals": [{"currency": "BYN", "amount": "1420.00"}]},
            {"role": "salary", "label": "Основная часть", "nominal_date": "2026-09-05", "effective_date": "2026-09-04", "shifted": True, "status": "actual", "actual_operations": [salary], "actual_totals": [{"currency": "BYN", "amount": "2854.78"}]},
        ],
        "extras": [], "totals": [{"currency": "BYN", "actual_amount": "4274.78", "forecast_amount": "0", "expected_amount": "4274.78", "extras_amount": "0"}],
        "earnings_estimate": {"status": "actual", "reason": None, "currency": "BYN", "planned_days": 21, "planned_hours": "168.00", "basis_amount": "4274.78", "daily_amount": "203.56", "hourly_amount": "25.45"},
    }
    days = [{"date": f"2026-09-{day:02}", "weekday": (day + 1) % 7, "status": "workday", "status_label": "Рабочий день", "planned_hours": "8", "actual_hours": "4.5" if day == 7 else "8", "credited_hours": "4.5" if day == 7 else "8", "is_workday": True, "is_live": day == 7, "is_completed": day != 7, "hours_state": "live" if day == 7 else "actual"} for day in [1, 2, 3, 4, 7]]
    snapshot = {
        "year": 2026, "month": 9, "profile": {"standard_hours_per_day": "8", "workweek_days": [0, 1, 2, 3, 4], "workday_start_time": "09:00", "workday_end_time": "18:00", "lunch_start_time": "13:00", "lunch_end_time": "14:00", "advance_plan_id": 3, "salary_plan_id": 4},
        "summary": {"planned_hours": "176", "actual_hours": "36.5", "credited_hours": "36.5", "planned_days": 22, "completed_days": 4, "override_days": 0},
        "days": days, "salary_cycle": cycle, "payroll_operations": [salary],
        "payments": [{"role": "salary", "effective_date": "2026-09-04", "actual_operations": [salary]}, {"role": "advance", "effective_date": "2026-09-18", "forecast_visible": True, "forecast_amount": "1420.00", "forecast_currency": "BYN"}],
    }

    def respond(route, payload):
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def handler(route, req):
        path = urlparse(req.url).path
        if path == "/api/v1/work/month":
            return respond(route, snapshot)
        if path in {"/api/v1/work/contracts", "/api/v1/work/companies"}:
            return respond(route, [])
        if path == "/api/v1/work/statistics":
            return respond(route, {"months": []})
        if path.startswith("/api/v1/work/payments/"):
            return respond(route, {"items": [], "total": 0})
        route.fallback()

    page.route("**/api/v1/work/**", handler)
    page.route("**/api/v1/operations/catalog-products?*", lambda route: respond(route, {"items": [], "total": 0}))
    page.route("**/api/v1/plans?*", lambda route: respond(route, {"items": [{"id": 3, "note": "Аванс", "amount": "1420", "currency": "BYN"}, {"id": 4, "note": "Основная часть", "amount": "2854.78", "currency": "BYN"}]}))
    page.goto(f"{url}/static/index.html")
    page.evaluate("window.Telegram = {WebApp: {initData: 'mock-init-data', ready() {}, expand() {}}}")
    _login(page)
    page.evaluate("window.App.getRuntimeModule('navigation').switchSection('work')")
    page.evaluate("window.App.getRuntimeModule('work').loadWorkSection()")
    page.evaluate("window.App.getRuntimeModule('work').setView('timesheet')")
    expect(page.locator(".work-salary-cycle-title strong")).to_have_text(cycle["label"])
    return page, snapshot


@pytest.mark.e2e
@pytest.mark.parametrize("width", [390, 768, 1280, 1920])
def test_work_cycle_kpis_keep_one_period_and_fit_viewport(request, width):
    page, _ = request.getfixturevalue("work_page")
    page.set_viewport_size({"width": width, "height": 1100})
    expect(page.locator("#workTimesheetPeriodTitle")).to_contain_text("сентябрь 2026")
    expect(page.locator("#workSummaryGrid article")).to_have_count(2)
    expect(page.locator("#workSummaryGrid article").nth(1)).to_contain_text("4 из 22")
    expect(page.locator("#workSummaryGrid")).to_contain_text("сегодня в процессе")
    kpis = page.locator("#workMoneySummaryGrid .work-money-kpi-card")
    expect(kpis).to_have_count(3)
    expect(kpis.nth(0)).to_contain_text("4 274,78")
    expect(kpis.nth(1).locator("strong")).to_contain_text("0,00")
    expect(kpis.nth(2)).to_contain_text("4 274,78")
    expect(page.locator(".work-earnings-values")).to_contain_text("203,56")
    expect(page.locator(".work-earnings-values")).to_contain_text("25,45")
    expect(page.locator(".work-earnings-estimate")).to_contain_text("21 дн. / 168 ч")
    expect(page.locator("#workPaymentsGrid .work-salary-cycle-component")).to_have_count(3)
    expect(page.locator("#workPaymentsGrid")).to_contain_text("20.08.2026")
    expect(page.locator("#workPaymentsGrid")).not_to_contain_text("18.09.2026")
    expect(page.locator("#workPaymentsGrid .work-payment-card")).to_have_count(0)
    panel = page.locator(".work-hero-panel")
    expect(panel).not_to_contain_text("Получено за месяц")
    expect(panel).not_to_contain_text("К оплате")
    expect(panel).not_to_contain_text("Исключения")
    assert panel.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
    assert panel.evaluate("el => [...el.querySelectorAll('.analytics-kpi-card, .work-salary-cycle-component')].every(n => n.getBoundingClientRect().right <= el.getBoundingClientRect().right + 1)")
    panel.screenshot(path=f"/tmp/work-cycle-kpis-{width}.png")


@pytest.mark.e2e
def test_cycle_actions_and_live_day_counter(request):
    page, _ = request.getfixturevalue("work_page")
    page.evaluate("window.App.getRuntimeModule('operations').openMoneyFlowSource = async value => { window.openedWorkPayment = value; }")
    page.click('#workPaymentsGrid [data-work-operation-id="701"]')
    assert page.evaluate("window.openedWorkPayment") == {"sourceKind": "operation", "sourceId": 701, "mode": "edit"}
    page.click('#workPaymentsGrid [data-work-open-plan-picker="advance"]')
    expect(page.locator("#workSettingsForm")).to_be_visible()
    expect(page.locator("#workAdvancePlan")).to_have_value("3")
    page.evaluate("window.App.getRuntimeModule('work').setView('timesheet')")
    before = page.locator("#workMoneySummaryGrid").inner_text()
    page.clock.fast_forward(5 * 60 * 60 * 1000)
    expect(page.locator("#workSummaryGrid article").nth(1)).to_contain_text("5 из 22")
    expect(page.locator("#workSummaryGrid article").nth(0)).to_contain_text("40 из 176")
    expect(page.locator("#workSummaryGrid")).not_to_contain_text("сегодня в процессе")
    assert page.locator("#workMoneySummaryGrid").inner_text() == before


@pytest.mark.e2e
@pytest.mark.parametrize("mode", ["forecast", "missing", "currency"])
def test_cycle_kpis_explain_forecast_and_unavailable_rates(request, mode):
    page, snapshot = request.getfixturevalue("work_page")
    cycle = snapshot["salary_cycle"]
    component = cycle["components"][1]
    component.update(status="missing" if mode == "missing" else "forecast", actual_operations=[], actual_totals=[], forecast_amount=None if mode == "missing" else "1200", forecast_currency="EUR" if mode == "currency" else "BYN")
    cycle["totals"] = [{"currency": "BYN", "actual_amount": "1420", "forecast_amount": "1200" if mode == "forecast" else "0", "expected_amount": "2620" if mode == "forecast" else "1420", "extras_amount": "0"}]
    if mode == "currency":
        cycle["totals"].append({"currency": "EUR", "actual_amount": "0", "forecast_amount": "1200", "expected_amount": "1200", "extras_amount": "0"})
    cycle["earnings_estimate"].update(status="forecast" if mode == "forecast" else "unavailable", reason=None if mode == "forecast" else "missing_payment" if mode == "missing" else "unresolved_currency", daily_amount="124.76" if mode == "forecast" else None, hourly_amount="15.60" if mode == "forecast" else None)
    page.evaluate("window.App.getRuntimeModule('work').loadWorkSection({refresh:true})")
    if mode == "forecast":
        expect(page.locator(".work-earnings-estimate")).to_contain_text("С учётом прогноза")
        expect(page.locator(".work-earnings-values")).to_contain_text("124,76")
        expect(page.locator(".work-money-kpi-forecast")).to_contain_text("1 200,00")
    else:
        expect(page.locator(".work-earnings-values")).to_contain_text("Недостаточно данных")
        expect(page.locator(".work-earnings-values")).not_to_contain_text("203,56")
        if mode == "missing":
            expect(page.locator(".work-money-kpi-forecast .work-money-kpi-values")).to_have_text("—")
            expect(page.locator("#workMoneySummaryGrid")).to_contain_text("Неполный итог")
        else:
            expect(page.locator(".work-earnings-estimate")).to_contain_text("Нет пересчёта всей зарплаты в BYN")
