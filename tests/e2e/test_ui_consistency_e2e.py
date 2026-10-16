"""Shared settings remain keyboard-operable and persist through navigation."""
import pytest
from playwright.sync_api import expect
from tests.e2e.test_directories_settings_e2e import directory_page, static_server_url


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 1440])
def test_settings_switches_and_selection_chips_save(directory_page, width):
    page, *_ = directory_page
    page.set_viewport_size({'width': width, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    # Await the initial settings render before editing its native fields.
    page.wait_for_function("window.App.state.preferences?.data?.ui?.active_section === 'settings'")
    page.locator('[data-settings-view=dashboard]').click()
    toggle = page.get_by_role('switch', name='Планы', exact=True)
    before = toggle.is_checked()
    toggle.focus(); toggle.press('Space')
    assert toggle.is_checked() != before
    assert toggle.evaluate("n=>getComputedStyle(n).appearance") == 'none'
    page.screenshot(path=f'/tmp/fa-ui-settings-switch-{width}.png')
    page.locator('[data-settings-view=currency]').click()
    expect(page.locator('#showDashboardOperationsToggle')).to_be_checked(checked=not before)
    usd = page.get_by_role('checkbox', name='USD', exact=True)
    usd.uncheck()
    eur = page.get_by_role('checkbox', name='EUR', exact=True)
    eur.check()
    bank = page.get_by_role('checkbox', name='БСБ Банк · наличные', exact=True)
    bank.uncheck()
    page.screenshot(path=f'/tmp/fa-ui-settings-chips-{width}.png')
    page.locator('[data-settings-view=notifications]').click()
    expect(page.locator('#showDashboardOperationsToggle')).to_be_checked(checked=not before)
    digest = page.get_by_role('switch', name='Ежедневные курсы в Telegram')
    digest.check()
    with page.expect_request(lambda r: '/api/v1/preferences' in r.url and r.method == 'PUT') as saved:
        page.locator('#saveSettingsBtn').click()
    prefs = saved.value.post_data_json['data']
    assert prefs['ui']['show_dashboard_operations'] != before
    assert 'USD' not in prefs['currency']['tracked_currencies']
    assert 'EUR' in prefs['currency']['tracked_currencies']
    assert 'bsb' not in prefs['currency']['bank_rate_banks']
    assert prefs['currency']['telegram_digest_enabled'] is True
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert not errors


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 1440])
def test_section_headers_and_shared_controls_fit(directory_page, width):
    page, *_ = directory_page
    page.set_viewport_size({'width': width, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    # This layout fixture predates the currency/work API; supply valid empty sections.
    page.route('**/api/v1/currency/overview?*', lambda r: r.fulfill(json={
        'base_currency': 'BYN', 'tracked_currencies': ['USD', 'EUR'],
        'positions': [], 'current_rates': [], 'recent_trades': [],
    }))
    page.route('**/api/v1/currency/trades?*', lambda r: r.fulfill(json={'items': [], 'total': 0}))
    page.route('**/api/v1/currency/performance/history?*', lambda r: r.fulfill(json={'items': []}))
    page.route('**/api/v1/work/month?*', lambda r: r.fulfill(json={
        'year': 2026, 'month': 10, 'profile': {'workweek_days': [0, 1, 2, 3, 4]},
        'summary': {}, 'days': [], 'payments': [],
    }))
    for resource in ['contracts', 'companies']:
        page.route('**/api/v1/work/' + resource, lambda r: r.fulfill(json=[]))
    page.route('**/api/v1/work/statistics?*', lambda r: r.fulfill(json={'months': [], 'earnings': {'totals': []}}))
    page.route('**/api/v1/work/payments/history?*', lambda r: r.fulfill(json={'items': [], 'total': 0}))
    for section in ['dashboard', 'analytics', 'operations', 'currency', 'plans', 'debts', 'categories', 'item_catalog', 'work', 'admin', 'settings']:
        page.evaluate("id => window.App.getRuntimeModule('navigation').switchSection(id)", section)
        expect(page.locator('#sectionTitle')).not_to_be_empty()
        expect(page.locator('#sectionSubtitle')).to_be_hidden()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), section
        if section == 'work':
            page.locator('[data-work-view=settings]').click()
            picker = page.locator('#workWeekdayPicker')
            picker.get_by_role('checkbox', name='Сб', exact=True).check()
            expect(picker.get_by_role('checkbox', name='Сб', exact=True)).to_be_checked()
        page.screenshot(path=f'/tmp/fa-ui-{section}-{width}.png')
    assert not errors
