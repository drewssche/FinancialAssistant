from datetime import date
import pytest
from playwright.sync_api import expect
from tests.e2e.test_plans_ui_e2e import static_server_url, page_with_plans_api_mock, _login_and_open_dashboard


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1440])
def test_period_cards_plans_and_rate_no_duplicates(static_server_url,page_with_plans_api_mock,width):
    p,state=page_with_plans_api_mock
    p.set_viewport_size({'width':width,'height':1000})
    errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    today=date.today().isoformat()
    state['plans'][:]=[dict(id=i,kind='expense',amount='10',scheduled_date=today,
        recurrence_enabled=False,status='due',confirm_count=0,skip_count=0) for i in range(1,13)]
    p.route('**/api/v1/dashboard/analytics/highlights?*',lambda r:r.fulfill(json=dict(
        period='month',date_from=today,date_to=today,income_total='100',expense_total='36',balance='64',
        cashflow_income_total='150',cashflow_expense_total='56',cashflow_total='94',
        prev_cashflow_income_total='80',prev_cashflow_expense_total='40',prev_cashflow_total='40',
        debt_cashflow_total='30',operations_count=2,cashflow_events_count=4,avg_daily_expense='2',
        category_breakdown=[],top_categories=[],top_positions=[],frequent_positions=[],price_increases=[])))
    p.route('**/api/v1/plans/forecast?*',lambda r:r.fulfill(json=dict(date_from=today,date_to=today,
        income_total='100',expense_total='70' if 'days=7' in r.request.url else '120',occurrences_count=12,overdue_count=0)))
    p.route('**/api/v1/currency/overview?*',lambda r:r.fulfill(json=dict(tracked_currencies=['RUB'],positions=[],
        current_rates=[dict(currency='RUB',rate='.03',change_value='.0001',change_pct='.3',rate_date=today)],bank_rates=[])))
    _login_and_open_dashboard(p,static_server_url)
    expect(p.locator('#dashboardKpiPrimary .analytics-kpi-card')).to_have_count(3)
    expect(p.locator('#dashboardKpiPrimary')).to_contain_text('150')
    expect(p.locator('#dashboardKpiPrimary')).to_contain_text('56')
    expect(p.locator('#dashboardKpiPrimary')).to_contain_text('94')
    expect(p.locator('#dashboardKpiPrimary')).not_to_contain_text('Сэкономлено')
    expect(p.locator('#dashboardKpiSecondary')).not_to_contain_text('Самый затратный')
    expect(p.locator('#dashboardPlansKpi')).to_contain_text('Планов: 12')
    expect(p.locator('#dashboardPlansKpi')).to_contain_text('120')
    expect(p.locator('#dashboardCurrencyRates .dashboard-currency-rate-badge')).to_have_count(0)
    expect(p.locator('#dashboardCurrencyRates .dashboard-currency-rate-delta').first).to_contain_text('+0.0100')
    assert p.locator('#dashboardSection').evaluate('n=>n.firstElementChild.id')=='dashboardAnalyticsPanel'
    assert p.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    p.locator('#dashboardAnalyticsPanel').screenshot(path=f'/tmp/fa-period-kpi-{width}.png')
    p.evaluate("window.App.getRuntimeModule('navigation').switchSection('plans')")
    expect(p.locator('#plansForecast')).to_contain_text('120')
    p.locator('[data-plans-horizon="7"]').click()
    expect(p.locator('#plansForecast')).to_contain_text('70')
    expect(p.locator('#plansKpiGrid')).not_to_contain_text('После планов')
    assert p.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    p.locator('#plansKpiGrid').screenshot(path=f'/tmp/fa-plans-forecast-{width}.png')
    content = p.evaluate("""()=>window.App.core.createMoneyFlowRow({id:'fx:1',source_id:1,source_kind:'fx',flow_direction:'outflow',event_date:'2026-10-18',amount:30,currency:'BYN',base_currency:'BYN',title:'Покупка USD',asset_currency:'USD',quote_currency:'BYN',trade_side:'buy'}).textContent""")
    assert content.count('Покупка USD') == 1
    assert not errors
