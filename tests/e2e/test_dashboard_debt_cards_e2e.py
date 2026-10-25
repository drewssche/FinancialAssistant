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
    p.locator("#dashboardDebtsPanel").scroll_into_view_if_needed()
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

@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,768,1024,1440])
def test_counterparty_columns_align_with_different_amounts_notes_and_due_dates(static_server_url,page_with_debts_api_mock,width):
    p=page_with_debts_api_mock;p.set_viewport_size({'width':width,'height':1000})
    cards=[]
    for i,(name,amount,note,due) in enumerate([
        ('Артём','100.00','Сказал отдаст после обеда','2026-11-01'),
        ('Мама','500.00','1/3 за стиральную машину','2026-11-05'),
        ('Ник','25.00','На мойку АТ',None),
        ('Длинное имя контрагента','1234567.89','Очень длинный комментарий '+('безпробелов'*12),'2026-12-31'),
    ]):
        debt={'id':9001+i,'counterparty_id':i+1,'direction':'borrow' if i==1 else 'lend',
              'principal':amount,'repaid_total':'0.00','outstanding_total':amount,'currency':'BYN',
              'start_date':'2026-09-13','due_date':due,'note':note,'repayments':[],'issuances':[],'forgivenesses':[]}
        cards.append({'counterparty_id':i+1,'counterparty':name,'status':'active','principal_total':amount,
                      'repaid_total':'0.00','outstanding_total':amount,'nearest_due_date':due,'debts':[debt]})
    p.route('**/api/v1/dashboard/debts/preview?**',lambda r:r.fulfill(json=cards))
    p.route('**/api/v1/debts/cards?**',lambda r:r.fulfill(json=cards))
    p.route('**/api/v1/operations/catalog-products*',lambda r:r.fulfill(json={'items':[],'total':0}))
    p.goto(static_server_url+'/static/index.html');_login_via_mock_telegram(p)
    for section,selector in [('dashboard','#dashboardDebtsList'),('debts','#debtsCards')]:
        if section=='debts':p.evaluate("window.App.getRuntimeModule('navigation').switchSection('debts')")
        root=p.locator(selector);expect(root.locator('.debt-card')).to_have_count(4)
        root.scroll_into_view_if_needed()
        assert root.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
        if width>640:
            positions=root.locator('thead tr').evaluate_all('''rows=>rows.map(row=>[...row.children].filter(c=>c.getBoundingClientRect().width).map(c=>({x:c.getBoundingClientRect().x,w:c.getBoundingClientRect().width})))''')
            for group in positions[1:]:
                assert len(group)==len(positions[0])
                for actual,expected in zip(group,positions[0]):
                    assert abs(actual['x']-expected['x'])<1 and abs(actual['w']-expected['w'])<1
            assert root.locator('td').evaluate_all('cells=>cells.every(c=>!c.getBoundingClientRect().width||c.scrollWidth<=c.clientWidth+1)')
        if width > 640:
            offsets = root.locator('tr.debt-record-row').evaluate_all("""rows => rows.map(row =>
                row.querySelector('.debt-direct-actions').getBoundingClientRect().top - row.getBoundingClientRect().top)""")
            assert max(offsets) - min(offsets) < 1
        else:
            for entry in root.locator('.debt-mobile-entry').all():
                assert entry.locator('.debt-mobile-entry-note').bounding_box()['y'] >= entry.locator('.debt-direct-actions').bounding_box()['y'] + entry.locator('.debt-direct-actions').bounding_box()['height']
        for button in root.locator('.debt-direct-actions button').all():
            b=button.bounding_box();box=root.bounding_box()
            assert b and b['x']>=box['x']-1 and b['x']+b['width']<=box['x']+box['width']+1
        root.screenshot(path=f'/tmp/fa-debt-columns-{section}-{width}.png')
