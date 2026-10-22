from datetime import date
import pytest
from playwright.sync_api import expect
from tests.e2e.test_plans_ui_e2e import static_server_url, page_with_plans_api_mock, _login_and_open_dashboard


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1000,1440])
def test_debt_date_controls_fit_input(static_server_url,page_with_plans_api_mock,width,tmp_path):
    p,_=page_with_plans_api_mock;p.set_viewport_size({'width':width,'height':1000})
    p.route('**/api/v1/operations/catalog-products?*',lambda r:r.fulfill(json=[]))
    _login_and_open_dashboard(p,static_server_url)
    p.evaluate("window.App.actions.openCreateModal({entryMode:'debt'})")
    expect(p.locator('#createDebtFields')).to_be_visible()
    p.screenshot(path=f'{tmp_path}/debt-{width}.png')
    for field in ['debtStartDateField','debtDueDateField']:
        box=p.locator('#'+field+' input').bounding_box()
        for btn in p.locator('#'+field+' button').all():
            if not btn.is_visible():continue
            b=btn.bounding_box()
            assert abs((b['y']+b['height']/2)-(box['y']+box['height']/2))<1
            assert b['y']>=box['y']+4
            assert b['y']+b['height']<=box['y']+box['height']-4
            assert b['x']>=box['x']+4
            assert b['x']+b['width']<=box['x']+box['width']-4
    assert p.locator('#createModal').evaluate('n=>n.scrollWidth<=n.clientWidth+1')


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1440])
def test_plan_and_debt_net_use_displayed_base_totals(static_server_url,page_with_plans_api_mock,width,tmp_path):
    p,state=page_with_plans_api_mock;p.set_viewport_size({'width':width,'height':1000})
    today=date.today().isoformat()
    p.route('**/api/v1/plans/forecast?*',lambda r:r.fulfill(json=dict(date_from=today,date_to=today,
        income_total='100.10',expense_total='70.05' if 'days=7' in r.request.url else '120.30',
        occurrences_count=3,unpriced_count=1,overdue_count=0)))
    state['debt_cards'][:]=[dict(counterparty='Тест',counterparty_id=1,status='active',debts=[
        dict(id=1,direction='lend',principal='100',outstanding_total='100',currency='USD',base_currency='BYN',current_base_outstanding_total='300',start_date=today),
        dict(id=2,direction='borrow',principal='120',outstanding_total='120',currency='BYN',base_currency='BYN',current_base_outstanding_total='120',start_date=today),
        dict(id=3,direction='lend',principal='50',outstanding_total='0',currency='BYN',base_currency='BYN',current_base_outstanding_total='0',start_date=today),
    ])]
    p.route('**/api/v1/operations/catalog-products?*',lambda r:r.fulfill(json=[]))
    _login_and_open_dashboard(p,static_server_url)
    p.evaluate("window.App.getRuntimeModule('navigation').switchSection('plans')")
    expect(p.locator('[data-plans-net] strong')).to_contain_text('-20,20')
    expect(p.locator('[data-plans-net] strong')).to_have_class('amount-expense')
    expect(p.locator('#plansForecast')).to_contain_text('Без курса: 1')
    p.locator('[data-plans-horizon="7"]').click()
    expect(p.locator('[data-plans-net] strong')).to_contain_text('30,05')
    expect(p.locator('[data-plans-net] strong')).to_have_class('amount-income')
    p.locator('#plansKpiGrid').screenshot(path=f'{tmp_path}/plans-{width}.png')
    p.evaluate("window.App.getRuntimeModule('navigation').switchSection('debts')")
    expect(p.locator('[data-debts-net] strong')).to_contain_text('180,00')
    expect(p.locator('[data-debts-net] strong')).to_have_class('amount-income')
    p.locator('#debtsSectionKpi').screenshot(path=f'{tmp_path}/debts-kpi-{width}.png')
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    for lend,expected,css in [(0,'-120,00','amount-expense'),(120,'0,00','')]:
        p.evaluate('''lend=>{
          const cards=window.App.state.debtCardsCache;
          cards[0].debts.find(d=>d.id===1).current_base_outstanding_total=lend;
          window.App.debtCardsRenderer.renderDebtCards(cards);
        }''',lend)
        expect(p.locator('[data-debts-net] strong')).to_contain_text(expected)
        expect(p.locator('[data-debts-net] strong')).to_have_class(css)
