import json
import re
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import sync_playwright, expect
from tests.e2e.test_mobile_shell_cards_e2e import (
    static_server_url as static_server_url, _build_handler, _set_mock_telegram, _login_via_mock_telegram,
)


@pytest.fixture
def directory_page(static_server_url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        _set_mock_telegram(page)
        page.route('**/api/v1/**', _build_handler('settings'))
        page.route('**/api/v1/operations/catalog-products?*', lambda r: r.fulfill(json={'items': [], 'total': 0}))
        page.route('**/api/v1/users/me', lambda r: r.fulfill(json={'id': 1, 'is_admin': True, 'status': 'approved', 'display_name': 'Admin'}))
        calls = []
        pending = []
        control = {'hold': False, 'fail': False}
        def users(route):
            req = route.request
            calls.append((req.method, urlparse(req.url).path))
            if req.method != 'GET':
                return route.fulfill(json={})
            status = parse_qs(urlparse(req.url).query).get('status_filter', ['pending'])[0]
            payload = {'items': [{'id': 2, 'display_name': f'{status} — Пользователь с очень длинным именем и фамилией', 'username': 'test', 'status': status, 'telegram_id': '123456789'}]}
            if control['hold']:
                pending.append((route, payload))
            else:
                route.fulfill(json=payload)
        page.route(re.compile(r'/api/v1/admin/users(?:[/?].*)?$'), users)
        def diagnostics(route):
            calls.append(('GET', '/api/v1/admin/currency-diagnostics'))
            route.fulfill(status=500 if control['fail'] else 200, json={'items': [], 'detail': 'temporary'})
        page.route('**/api/v1/admin/currency-diagnostics', diagnostics)
        page.goto(static_server_url + '/static/index.html')
        _login_via_mock_telegram(page)
        yield page, calls, pending, control
        browser.close()


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1024, 1100, 1440])
def test_settings_pages_preserve_drafts_and_fit(directory_page, width):
    page, _, _, _ = directory_page
    page.set_viewport_size({'width': width, 'height': 900})
    page.locator('[data-settings-view="alerts"]').click()
    page.locator('#addBankCurrencyAlertBtn').click()
    page.locator('[data-bank-alert-threshold="above"]').fill('3.6000')
    page.locator('[data-bank-alert-choice="currency"][data-bank-alert-value="EUR"]').click()
    for view in ['data', 'currency', 'notifications', 'dashboard', 'general', 'alerts']:
        page.locator(f'[data-settings-view="{view}"]').click()
        expect(page.locator('[data-settings-panel]:visible')).to_have_count(1)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    expect(page.locator('[data-bank-alert-threshold="above"]')).to_have_value('3.6000')
    expect(page.locator('[data-bank-alert-choice="currency"][data-bank-alert-value="EUR"]')).to_have_class(__import__('re').compile('active'))
    page.locator('[data-settings-view="general"]').click()
    with page.expect_request(lambda r: '/api/v1/preferences' in r.url and r.method == 'PUT') as saved:
        page.locator('#saveSettingsBtn').click()
    rule = saved.value.post_data_json['data']['currency']['bank_rate_alerts'][0]
    assert rule['above_rate'] == '3.6000' and rule['currency'] == 'EUR'
    page.locator('[data-settings-view="data"]').click()
    expect(page.locator('#saveSettingsBtn')).to_be_hidden()
    expect(page.locator('#deleteMePhrase')).to_be_visible()


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1024, 1100, 1440])
def test_directories_visible_actions_and_search(directory_page, width):
    page, _, _, _ = directory_page
    page.set_viewport_size({'width': width, 'height': 900})
    page.evaluate('window.App.getRuntimeModule("navigation").switchSection("categories")')
    page.locator('#categoriesBody [data-edit-category-id="1"]').wait_for()
    expect(page.locator('#categorySearchQ')).to_have_value('')
    assert page.locator('#categorySearchQ').bounding_box()['height'] <= 48
    for button in page.locator('#categoriesBody .btn-icon').all():
        assert button.get_attribute('aria-label')
        box = button.bounding_box()
        if box:
            assert box['width'] >= (44 if width < 640 else 42)
    page.locator('#categorySearchQ').fill('Fkrjujkm')  # Алкоголь in the wrong layout
    expect(page.locator('#categoriesBody [data-edit-category-id="1"]')).to_be_visible()
    expect(page.locator('#categoriesBody [data-edit-category-id="2"]')).to_have_count(0)
    expect(page.locator('#categoriesKpiGrid')).to_contain_text('Категории 1')
    page.locator('#categoriesBody [data-edit-category-id="1"]').click()
    expect(page.locator('#editCategoryModal')).to_be_visible()
    page.locator('#closeEditCategoryModalBtn').click()
    page.locator('#categorySearchQ').fill('')
    page.locator('#categoriesCollapseAllBtn').click()
    expect(page.locator('#categoriesBody [data-edit-category-id="1"]')).to_be_hidden()
    page.locator('#categoriesExpandAllBtn').click()
    expect(page.locator('#categoriesBody [data-edit-category-id="1"]')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')


@pytest.mark.e2e
def test_admin_lazy_diagnostics_retry_latest_filter_and_delete_confirmation(directory_page):
    page, calls, pending, control = directory_page
    page.evaluate('window.App.getRuntimeModule("navigation").switchSection("admin")')
    expect(page.locator('#adminUsersBody')).to_contain_text('pending —')
    assert ('GET', '/api/v1/admin/currency-diagnostics') not in calls
    page.locator('[data-admin-approve-id="2"]').click()
    page.wait_for_timeout(300)
    page.wait_for_function('!document.querySelector("[data-admin-approve-id]")?.disabled')
    assert ('PATCH', '/api/v1/admin/users/2/status') in calls
    page.locator('[data-admin-delete-id="2"]').click()
    expect(page.locator('#confirmModal')).to_be_visible()
    page.locator('#confirmCancelBtn').click()
    assert ('DELETE', '/api/v1/admin/users/2') not in calls
    control['hold'] = True
    page.locator('[data-admin-user-status="approved"]').click()
    page.wait_for_timeout(100)
    page.locator('[data-admin-user-status="rejected"]').click()
    page.wait_for_timeout(100)
    assert len(pending) == 2
    pending[1][0].fulfill(json=pending[1][1])
    expect(page.locator('#adminUsersBody')).to_contain_text('rejected —')
    pending[0][0].fulfill(json=pending[0][1])
    expect(page.locator('#adminUsersBody')).to_contain_text('rejected —')
    control['fail'] = True
    page.locator('[data-admin-view="diagnostics"]').click()
    expect(page.locator('#adminUsersPanel')).to_be_hidden()
    control['fail'] = False
    page.locator('#refreshAdminCurrencyDiagnosticsBtn').click()
    expect(page.locator('#adminCurrencyDiagnosticsBody')).to_contain_text('Нет валютных настроек')
    expect(page.locator('#refreshAdminCurrencyDiagnosticsBtn svg')).to_have_count(1)


@pytest.mark.e2e
def test_settings_hidden_validation_and_failed_save_keep_draft(directory_page):
    page, _, _, _ = directory_page
    page.locator('[data-settings-view="alerts"]').click()
    field = page.locator('[data-currency-alert="USD"][data-currency-alert-kind="above"]')
    field.fill('-1')
    page.locator('[data-settings-view="general"]').click()
    page.locator('#saveSettingsBtn').click()
    expect(page.locator('#settings-alerts')).to_be_visible()
    expect(field).to_be_focused()
    field.fill('3.5')
    page.route('**/api/v1/preferences', lambda r: r.fulfill(status=500, json={'detail': 'temporary save error'}) if r.request.method == 'PUT' else r.fallback())
    with page.expect_response(lambda r: '/api/v1/preferences' in r.url and r.status == 500):
        page.locator('#saveSettingsBtn').click()
    expect(page.locator('#saveSettingsBtn')).to_be_enabled()
    expect(page.locator('#saveSettingsBtn svg')).to_have_count(1)
    expect(field).to_have_value('3.5')
    page.unroute('**/api/v1/preferences')
    with page.expect_response(lambda r: '/api/v1/preferences' in r.url and r.request.method == 'PUT' and r.status == 200):
        page.locator('#saveSettingsBtn').click()
