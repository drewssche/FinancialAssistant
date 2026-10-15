import pytest
from playwright.sync_api import expect
from tests.e2e.test_debts_flow_e2e import static_server_url, page_with_debts_api_mock, _login_via_mock_telegram


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1024, 1440])
def test_dashboard_debts_share_section_rows_and_resize(static_server_url, page_with_debts_api_mock, width):
    p=page_with_debts_api_mock;p.set_viewport_size({'width':width,'height':1000})
    errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    p.route('**/api/v1/operations/catalog-products*',lambda route:route.fulfill(json={'items':[],'total':0,'page':1,'page_size':100}))
    p.goto(static_server_url+'/static/index.html');_login_via_mock_telegram(p)
    action=p.locator('[data-dashboard-history-debt-id="9001"]');expect(action).to_be_visible()
    root=p.locator('#dashboardDebtsList')
    expect(root.locator('table')).to_have_count(0 if width<=640 else 1)
    root.scroll_into_view_if_needed()
    box=root.bounding_box()
    assert root.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    for button in root.locator('button').all():
        b=button.bounding_box();assert b['x']>=box['x'] and b['x']+b['width']<=box['x']+box['width']+1
    p.locator('#dashboardDebtsPanel').screenshot(path=f'/tmp/fa-dashboard-debts-{width}.png',animations='disabled')
    action.click();expect(p.locator('#debtHistoryModal')).to_be_visible();p.click('#closeDebtHistoryModalBtn')
    p.evaluate("window.App.getRuntimeModule('navigation').switchSection('debts')")
    expect(p.locator('#debtsCards [data-debt-row-id="9001"]')).to_be_visible()
    p.locator('#debtsCards').screenshot(path=f'/tmp/fa-section-debts-{width}.png',animations='disabled')
    p.evaluate("window.App.getRuntimeModule('navigation').switchSection('dashboard')")
    p.set_viewport_size({'width':1440 if width<=640 else 390,'height':1000})
    expect(root.locator('table')).to_have_count(1 if width<=640 else 0)
    p.locator('[data-dashboard-repay-debt-id="9001"]').click()
    expect(p.locator('#debtRepaymentModal')).to_be_visible()
    assert not errors
