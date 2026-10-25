import pytest
from playwright.sync_api import expect
from tests.e2e.test_directories_settings_e2e import directory_page,static_server_url


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_report_controls_roundtrip_pause_and_mobile_layout(directory_page,width):
    page,*_=directory_page
    page.set_viewport_size({'width':width,'height':1000})
    data={'available':True,'settings':{'enabled':True,'weekly':True,'monthly':True,'yearly':True,'telegram':True,'email':True,'send_time':'09:00'},'email_address':'owner-with-a-long-address@example.test','timezone':'Europe/Minsk','next_send':'2026-11-01T09:00:00+03:00'}
    saved=[]
    def handler(route):
        if route.request.method=='PUT':
            data['settings']=route.request.post_data_json;saved.append(data['settings'].copy())
            data['next_send']=None if not data['settings']['enabled'] else '2026-11-01T10:15:00+03:00'
        route.fulfill(json=data)
    page.route('**/api/v1/preferences/financial-reports',handler)
    page.locator('[data-settings-view="reports"]').click()
    expect(page.locator('#reportSettingsFields')).to_be_enabled()
    expect(page.locator('#saveSettingsBtn')).to_be_hidden()
    page.locator('#reportSettingsForm [name="send_time"]').select_option('10:15')
    page.locator('#reportSettingsForm [name="email"]').uncheck()
    page.locator('#saveReportSettings').click()
    expect(page.locator('#reportSettingsStatus')).to_have_text('Настройки рассылки сохранены.')
    assert saved[-1]['email'] is False and saved[-1]['send_time']=='10:15'
    page.locator('#reportSettingsForm [name="enabled"]').uncheck()
    page.locator('#saveReportSettings').click()
    expect(page.locator('#reportNextSend')).to_have_text('Рассылка приостановлена')
    page.locator('[data-settings-view="general"]').click()
    page.locator('[data-settings-view="reports"]').click()
    expect(page.locator('#reportSettingsForm [name="enabled"]')).not_to_be_checked()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    for selector in ['#reportSettingsForm select','#saveReportSettings']:
        b=page.locator(selector).bounding_box();assert b['x']>=0 and b['x']+b['width']<=width+1
    from pathlib import Path
    target=Path('docs/_local/report-settings-20261026');target.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(target/f'settings-{width}.png'),full_page=True)


@pytest.mark.e2e
def test_report_save_failure_keeps_draft_and_never_confirms_success(directory_page):
    page,*_=directory_page
    data={'available':True,'settings':{'enabled':True,'weekly':True,'monthly':True,'yearly':True,'telegram':True,'email':True,'send_time':'09:00'},'email_address':'owner@example.test','next_send':None}
    def handler(route):
        if route.request.method=='PUT':return route.fulfill(status=500,json={'detail':'temporary failure'})
        route.fulfill(json=data)
    page.route('**/api/v1/preferences/financial-reports',handler)
    page.locator('[data-settings-view="reports"]').click()
    page.locator('#reportSettingsForm [name="send_time"]').select_option('11:30')
    page.locator('#saveReportSettings').click()
    expect(page.locator('#reportSettingsStatus')).to_contain_text('temporary failure')
    expect(page.locator('#reportSettingsForm [name="send_time"]')).to_have_value('11:30')
    expect(page.locator('#saveReportSettings')).to_be_enabled()
