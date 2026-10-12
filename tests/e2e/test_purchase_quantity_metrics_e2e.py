import pytest
from playwright.sync_api import expect

from tests.e2e.test_analytics_mobile_e2e import (
    static_server_url, page_with_analytics_api_mock, _login_analytics,
)


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1440])
def test_comparable_metrics_currency_choice_and_legacy_preference(static_server_url, page_with_analytics_api_mock, width):
    page = page_with_analytics_api_mock
    page.set_viewport_size({'width': width, 'height': 1100})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    quantities = {'packs': '2', 'pieces': '0', 'mass_kg': '1.8', 'volume_l': '0', 'content_pieces': '0',
                  'unknown_rows_count': 0, 'rows_count': 2, 'unmeasured_package_rows_count': 0}
    unknown = {'rows_count': 1, 'unknown_rows_count': 1}
    buckets = [{'key': '2026-10-12', 'label': '12', 'date_from': '2026-10-12', 'date_to': '2026-10-12'}]
    rows = [
        {'product_id': 501, 'template_id': None, 'name': 'Крупа', 'shop_name': None, 'source_names': ['Грин', 'Соседи'],
         'purchases_count': 1, 'quantity_total': '2', 'quantity_totals': quantities, 'amount_total': '23.65',
         'amount_totals': {'BYN': '3.65', 'USD': '20'},
         'buckets': [{'key': buckets[0]['key'], 'purchases_count': 1, 'quantity_totals': quantities, 'amount_totals': {'BYN': '3.65', 'USD': '20'}}]},
        {'product_id': 502, 'template_id': None, 'name': 'Неизвестная фасовка', 'shop_name': 'Грин', 'source_names': ['Грин'],
         'purchases_count': 1, 'quantity_total': '99999', 'quantity_totals': unknown, 'amount_totals': {'BYN': '5'},
         'buckets': [{'key': buckets[0]['key'], 'purchases_count': 1, 'quantity_totals': unknown, 'amount_totals': {'BYN': '5'}}]},
    ]
    payload = {'period': 'month', 'anchor': '2026-10-12', 'date_from': '2026-10-01', 'date_to': '2026-10-31',
               'buckets': buckets, 'positions': rows,
               'summary': {'purchases_count': 2, 'quantity_totals': quantities | {'rows_count': 3, 'unknown_rows_count': 1},
                           'amount_totals': {'BYN': '8.65', 'USD': '20'}}}
    page.route('**/api/v1/dashboard/analytics/positions?**', lambda route: route.fulfill(json=payload))
    # Old untyped quantity preferences should become the useful receipts metric.
    page.route('**/api/v1/preferences', lambda route: route.fulfill(json={
        'preferences_version': 1, 'data': {'analytics': {'positions_metric_version': 2, 'positions_metric': 'quantity'}}
    }))
    page.goto(f'{static_server_url}/static/index.html')
    _login_analytics(page)
    page.evaluate("async () => { await window.App.actions.switchSection('analytics'); window.App.actions.setAnalyticsTab('positions'); await window.App.actions.loadAnalyticsPositions({force: true}); }")
    page.wait_for_selector('#analyticsPositionsPanel:not(.hidden)')
    expect(page.locator('#analyticsPositionsRankingTitle')).to_have_text('Чаще всего покупали')
    expect(page.locator('#analyticsPositionsSummary')).to_contain_text('Чеков с товарами')
    expect(page.locator('#analyticsPositionsSummary')).to_contain_text('Без единиц: 1 стр.')
    expect(page.locator('#analyticsPositionsSummary')).not_to_contain_text('99999')
    page.locator('[data-analytics-positions-metric="packs"]').click()
    expect(page.locator('#analyticsPositionsRanking .analytics-position-ranking-row').first).to_contain_text('2 упак.')
    page.locator('[data-analytics-positions-metric="mass_kg"]').click()
    expect(page.locator('#analyticsPositionsRanking .analytics-position-ranking-row').first).to_contain_text('1,8 кг')
    page.locator('#analyticsPositionsSourceSearch').fill('cjctlb')
    expect(page.locator('#analyticsPositionsRanking .analytics-position-ranking-row')).to_have_count(1)
    page.locator('#analyticsPositionsSourceSearch').fill('')
    page.locator('[data-analytics-positions-metric="amount"]').click()
    page.locator('#analyticsPositionsCurrency').select_option('USD')
    expect(page.locator('#analyticsPositionsRanking .analytics-position-ranking-value').first).to_contain_text('20')
    expect(page.locator('#analyticsPositionsRanking .analytics-position-ranking-row').first).to_contain_text('Крупа')
    metric_boxes = page.locator('#analyticsPositionsMetricTabs button').all()
    for button in metric_boxes:
        box = button.bounding_box()
        assert box['x'] >= 0 and box['x'] + box['width'] <= width + 1
    page.screenshot(path=f'/tmp/fa-quantities-{width}.png', full_page=True)
    # Opening product operations keeps the catalog grouping, not one arbitrary offer.
    page.locator('#analyticsPositionsMobileFocus [data-position-product-id="501"]').first.click() if width < 1000 else page.locator('#analyticsPositionsMatrixBody [data-position-product-id="501"]').first.click()
    page.wait_for_selector('#operationsSection:not(.hidden)')
    assert page.evaluate('window.App.state.operationsProductFilterId') == 501
    assert errors == []
