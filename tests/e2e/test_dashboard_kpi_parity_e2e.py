from datetime import date
import pytest
from playwright.sync_api import expect
from tests.e2e.test_plans_ui_e2e import static_server_url, page_with_plans_api_mock, _login_and_open_dashboard


def cards(page, selector):
    return page.locator(selector + ' > .analytics-kpi-card').all_text_contents()


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1440])
def test_dashboard_and_sections_share_plan_and_debt_kpis(static_server_url, page_with_plans_api_mock, width):
    p, state = page_with_plans_api_mock
    p.set_viewport_size({'width': width, 'height': 1000})
    errors = []
    p.on('pageerror', lambda e: errors.append(str(e)))
    today = date.today().isoformat()
    p.route('**/api/v1/plans/forecast?*', lambda r: r.fulfill(json=dict(
        date_from=today, date_to=today, income_total='100.10',
        expense_total='70.05' if 'days=7' in r.request.url else '120.30',
        occurrences_count=12, unpriced_count=1, overdue_count=2)))
    p.route('**/api/v1/dashboard/summary?*', lambda r: r.fulfill(json=dict(
        income_total='0', expense_total='0', debt_lend_outstanding='300',
        debt_borrow_outstanding='120', debt_net_position='180', debt_summary_available=True)))
    # Preview is deliberately empty: KPI totals must include all debts, not only preview rows.
    p.route('**/api/v1/dashboard/debts/preview?*', lambda r: r.fulfill(json=[]))
    state['debt_cards'][:] = [dict(counterparty='Тест', counterparty_id=1, status='active', debts=[
        dict(id=1, direction='lend', principal='100', outstanding_total='100', currency='USD', base_currency='BYN', current_base_outstanding_total='300', start_date=today),
        dict(id=2, direction='borrow', principal='120', outstanding_total='120', currency='BYN', base_currency='BYN', current_base_outstanding_total='120', start_date=today),
    ])]
    _login_and_open_dashboard(p, static_server_url)
    expect(p.locator('#dashboardPlansKpi [data-plans-net] strong')).to_have_text('-20,20\u00a0\ue901')
    expect(p.locator('#dashboardPlansKpi')).to_contain_text('Без курса: 1, не включены в суммы')
    expect(p.locator('#dashboardPlansKpi')).to_contain_text('Просрочено планов: 2')
    expect(p.locator('#debtNetTotal')).to_contain_text('180,00')
    plan_month = cards(p, '#dashboardPlansKpi')
    debt_summary = cards(p, '#dashboardDebtKpiGrid')
    assert len(plan_month) == len(debt_summary) == 3
    for block in ['dashboardPlansKpi', 'dashboardDebtKpiGrid']:
        node = p.locator('#' + block)
        node.scroll_into_view_if_needed()
        assert node.evaluate('n => n.scrollWidth <= n.clientWidth + 1')
        node.screenshot(path=f'/tmp/fa-sync-{block}-{width}.png')
    p.locator('[data-dashboard-plans-period="week"]').click()
    expect(p.locator('#dashboardPlansKpi [data-plans-net] strong')).to_contain_text('30,05')
    plan_week = cards(p, '#dashboardPlansKpi')
    p.evaluate("window.App.getRuntimeModule('navigation').switchSection('plans')")
    expect(p.locator('#plansForecast [data-plans-net] strong')).to_contain_text('-20,20')
    assert cards(p, '#plansForecast') == plan_month
    p.locator('[data-plans-horizon="7"]').click()
    expect(p.locator('#plansForecast [data-plans-net] strong')).to_contain_text('30,05')
    assert cards(p, '#plansForecast') == plan_week
    p.evaluate("window.App.getRuntimeModule('navigation').switchSection('debts')")
    expect(p.locator('#debtsSectionKpi [data-debts-net] strong')).to_contain_text('180,00')
    assert cards(p, '#debtsSectionKpi') == debt_summary
    assert p.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert not errors


@pytest.mark.e2e
def test_unavailable_dashboard_debt_summary_is_not_zero(static_server_url, page_with_plans_api_mock):
    p, _ = page_with_plans_api_mock
    p.route('**/api/v1/dashboard/summary?*', lambda r: r.fulfill(json=dict(
        debt_lend_outstanding='0', debt_borrow_outstanding='0', debt_net_position='0', debt_summary_available=False)))
    _login_and_open_dashboard(p, static_server_url)
    expect(p.locator('#dashboardDebtKpiGrid')).to_contain_text('Не удалось загрузить итоги долгов')
    expect(p.locator('#dashboardDebtKpiGrid .analytics-kpi-card')).to_have_count(0)
