import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url,page_with_receipt_api_mock,_login


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1440])
def test_regular_user_has_no_work_menu_direct_navigation_or_requests(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;p.set_viewport_size({'width':width,'height':1000});calls=[]
    p.route('**/api/v1/work/**',lambda r:(calls.append(r.request.url),r.fulfill(status=403,json={'detail':'Admin access required'})))
    p.goto(f'{static_server_url}/static/index.html')
    expect(p.locator('[data-section=work]')).to_be_hidden()
    p.evaluate("window.Telegram={WebApp:{initData:'mock-init-data',ready(){},expand(){}}}");_login(p)
    expect(p.locator('[data-section=work]')).to_be_hidden()
    expect(p.locator('.nav-group-title[data-admin-only]')).to_be_hidden()
    expect(p.locator('#adminNavBtn')).to_be_hidden()
    p.evaluate("window.App.getRuntimeModule('navigation').switchSection('work')")
    p.evaluate("window.App.getRuntimeModule('work').loadWorkSection()")
    expect(p.locator('#workSection')).to_be_hidden()
    assert p.evaluate('window.App.state.activeSection')=='dashboard'
    # A saved/stale active section is also rejected when applying navigation state.
    p.evaluate("window.App.state.activeSection='work';window.App.getRuntimeModule('navigation').applySectionUi()")
    assert p.evaluate('window.App.state.activeSection')=='dashboard'
    assert calls==[]


@pytest.mark.e2e
def test_admin_menu_is_visible_and_removed_on_logout(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock
    p.route('**/api/v1/users/me',lambda r:r.fulfill(json={'id':1,'display_name':'Admin','status':'approved','is_admin':True}))
    p.goto(f'{static_server_url}/static/index.html')
    p.evaluate("window.Telegram={WebApp:{initData:'mock-init-data',ready(){},expand(){}}}");_login(p)
    expect(p.locator('[data-section=work]')).to_be_visible()
    expect(p.locator('.nav-group-title[data-admin-only]')).to_be_visible()
    expect(p.locator('#adminNavBtn')).to_be_visible()
    p.evaluate('window.App.actions.logout(false)')
    assert p.evaluate('window.App.state.isAdmin') is False
    expect(p.locator('[data-section=work]')).to_have_class('nav-btn hidden')
    expect(p.locator('#workSection')).to_be_hidden()
