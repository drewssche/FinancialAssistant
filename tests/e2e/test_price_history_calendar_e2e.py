from datetime import date
import pytest
from playwright.sync_api import expect
from tests.e2e.test_product_primary_codes_e2e import setup
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock
from tests.e2e.test_analytics_mobile_e2e import page_with_analytics_api_mock, _open_mobile_analytics


@pytest.mark.e2e
@pytest.mark.parametrize('width', [390, 1440])
def test_website_history_separates_packages_and_receipt_total(static_server_url, page_with_receipt_api_mock, width):
    p = page_with_receipt_api_mock
    base = dict(url='https://green-dostavka.by/product/milk/', source='Green', available=True,
                unit='шт.', comparison_key='900ml', conditions_key='public', conditions='Общедоступная цена', normalized='900 мл')
    rows = [dict(base, id=i, recorded_at=f'2026-10-{i:02d}T10:00:00Z', price=price)
            for i, price in [(1,'2.90'),(2,'2.70'),(3,'2.80')]]
    p.route('**/catalog-watches/401', lambda r:r.fulfill(json={'enabled':False,'offers':[], 'supported_offer_ids':[501], 'supported_offers':{}}))
    p.route('**/catalog-watches/401/offers/501/history*', lambda r: r.fulfill(json={'items': rows, 'next_cursor': None}))
    setup(p, static_server_url, width)
    p.locator('[data-product-tab=prices]').click()
    p.locator('#catalogProductPriceMode').select_option('website')
    expect(p.locator('.product-price-chart')).to_be_visible()
    expect(p.locator('.product-price-summary')).to_contain_text('повышений: 1 · снижений: 1')
    expect(p.locator('#catalogProductPricesList [data-product-purchase-id]')).to_have_count(0)
    chart = p.locator('.product-price-chart'); chart.focus(); chart.press('End')
    expect(p.locator('.analytics-chart-tooltip:not(.hidden)')).to_contain_text('2,8 BYN / шт.'.replace(' / ', '/'))
    assert chart.locator('.product-price-line').get_attribute('d').count('H') == 2
    p.locator('#catalogProductModal').screenshot(path=f'/tmp/fa-site-history-{width}.png')
    p.locator('#closeCatalogProductModalBtn').click()
    p.evaluate('''()=>window.App.actions.openOperationReceiptModal({id:77,amount:'47.14',currency:'BYN',operation_date:'2026-10-18',receipt_items:[
      {name:'Чипсы Lays Лосось 140г',quantity:1,unit_price:4.49},
      {name:'Кофе Nescafe Gold 190г',quantity:1,unit_price:22.99}]})''')
    total = p.locator('.operation-receipt-total').first
    expect(total).to_be_visible()
    assert total.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)') >= 17
    assert p.locator('#operationReceiptItems').evaluate('n=>n.scrollWidth <= n.clientWidth+1')
    p.locator('#operationReceiptModal').screenshot(path=f'/tmp/fa-receipt-prices-{width}.png')


@pytest.mark.e2e
@pytest.mark.parametrize('width', [390, 1440])
def test_all_time_grid_and_kpis_drill_into_year(static_server_url, page_with_analytics_api_mock, width):
    p = page_with_analytics_api_mock
    totals = dict(income_total='100',expense_total='40',balance='60',cashflow_income_total='190',cashflow_expense_total='70',cashflow_total='120',cashflow_events_count=4)
    p.route('**/dashboard/analytics/calendar/all-time', lambda r:r.fulfill(json=dict(totals, date_from='2025-02-01',date_to=date.today().isoformat(),years=[dict(totals,year=2025)])))
    _open_mobile_analytics(p, static_server_url)
    p.set_viewport_size({'width':width,'height':1000})
    p.locator('[data-analytics-tab=calendar]').click()
    p.locator('[data-analytics-calendar-view=all_time]').click()
    expect(p.locator('[data-calendar-year="2025"]')).to_be_visible()
    expect(p.locator('#analyticsCalendarTotals')).to_contain_text('Пришло')
    expect(p.locator('#analyticsCalendarTotals')).to_contain_text('Ушло')
    expect(p.locator('#analyticsCalendarTotals')).to_contain_text('Разница')
    expect(p.locator('#analyticsCalendarTotals')).not_to_contain_text('Профицит')
    expect(p.locator('#analyticsPrevGridBtn')).not_to_be_visible()
    assert p.locator('#analyticsCalendarTotals').evaluate('n=>n.scrollWidth <= n.clientWidth+1')
    assert p.locator('[data-calendar-year="2025"]').evaluate('n=>n.scrollHeight <= n.clientHeight+1')
    p.locator('#analyticsCalendarPanel').screenshot(path=f'/tmp/fa-calendar-all-time-{width}.png')
    p.locator('[data-calendar-year="2025"]').click()
    expect(p.locator('[data-analytics-calendar-view=year]')).to_have_class('segmented-btn active')
    expect(p.locator('#analyticsYearGrid .analytics-year-card')).not_to_have_count(0)


from tests.e2e.test_plans_ui_e2e import page_with_plans_api_mock, _login_and_open_dashboard


@pytest.mark.e2e
@pytest.mark.parametrize('width', [390, 1440])
def test_dashboard_rate_shows_last_publication_and_opens_by_keyboard(static_server_url, page_with_plans_api_mock, width):
    page, _ = page_with_plans_api_mock
    page.set_viewport_size({'width': width, 'height': 1000})
    page.route('**/api/v1/dashboard/currency-rates', lambda route: route.fulfill(json=[
        dict(currency='USD', display_scale=1, display_rate='3.0091', change_pct=0, rate_date='2025-01-01')]))
    _login_and_open_dashboard(page, static_server_url)
    row = page.locator('[data-dashboard-quote=USD]')
    expect(page.locator('#dashboardCurrencyDate')).to_have_text('НБРБ на 01.01.2025')
    expect(row).to_contain_text('0,00 %')
    row.focus()
    expect(row).to_be_focused()
    row.press('Enter')
    expect(page.locator('[data-quote-currency=USD]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#currencyQuotesList caption')).to_have_text('BYN за 1 USD')
