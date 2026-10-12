from urllib.parse import urlparse
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login, _ensure_categories_loaded


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1440])
def test_explicit_variant_selection_and_historical_edit(static_server_url, page_with_receipt_api_mock, width):
    page = page_with_receipt_api_mock
    page.set_viewport_size({'width': width, 'height': 1100})
    variants = [dict(id=91, name='Пакет 900 мл', sale_unit='pack', package_quantity='900', package_unit='ml', codes=['04006381333931']),
                dict(id=92, name='Пакет 500 мл', sale_unit='pack', package_quantity='500', package_unit='ml', codes=[]),
                dict(id=93, name='Архив', is_archived=True, codes=[])]
    requests = []; errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    def handler(route, req):
        path = urlparse(req.url).path
        if path.endswith('/401/identity'):
            requests.append(path)
            return route.fulfill(json={'variants': variants, 'offers': []})
        if path.endswith('/catalog-products'):
            return route.fulfill(json={'items': [], 'total': 0, 'page': 1, 'page_size': 100})
        route.fallback()
    page.route('**/api/v1/operations/**', handler)
    page.goto(f'{static_server_url}/static/index.html')
    page.evaluate("window.Telegram = {WebApp:{initData:'mock-init-data',ready(){},expand(){}}}")
    _login(page); _ensure_categories_loaded(page)
    page.click('#addOperationCta')
    page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
    page.evaluate('''() => {
      const modal = window.App.getRuntimeModule('operation-modal');
      window.App.state.createReceiptItems = [modal.createReceiptDraft({name:'Молоко', product_id:401, product_name:'Молоко', quantity:2, unit_price:3.25, details_expanded:true})];
      modal.renderReceiptItems('create');
    }''')
    row = page.locator('#receiptItemsList .receipt-item-row').first
    row.locator('.receipt-measurements summary').click()
    assert requests == []
    row.locator('[data-receipt-variants-load]').click()
    selector = row.locator('[data-receipt-field="variant_id"]')
    expect(selector.locator('option')).to_have_count(3)
    expect(selector).to_have_value('')
    selector.select_option('91')
    expect(row.locator('[data-receipt-field="package_quantity"]')).to_have_value('900')
    expect(row.locator('[data-receipt-variant-snapshot]')).to_contain_text('04006381333931')
    payload = page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert payload['variant_id'] == 91
    assert payload['variant_snapshot']['codes'] == ['04006381333931']
    assert payload['quantity'] == '2' and payload['unit_price'] == '3.25'
    for control in row.locator('.receipt-variant-controls button, .receipt-variant-controls select').all():
        box = control.bounding_box()
        assert box['x'] >= 0 and box['x'] + box['width'] <= width + 1
    page.screenshot(path=f'/tmp/fa-receipt-variant-{width}.png')
    # Changing registry data or archiving a variant cannot rewrite a saved receipt.
    variants[0].update(name='Пакет 800 мл', package_quantity='800', codes=[], is_archived=True)
    payload.pop('variant_id')
    page.evaluate('''async receipt => {
      window.App.actions.closeCreateModal();
      await window.App.getRuntimeModule('operation-modal').openEditModal({id:777, kind:'expense', amount:'6.50', original_amount:'6.50', currency:'BYN', operation_date:'2026-10-13', receipt_items:[receipt]});
    }''', payload)
    saved = page.locator('#editReceiptItemsList .receipt-item-row').first
    saved.locator('[data-receipt-details-toggle]').click()
    saved.locator('.receipt-measurements summary').click()
    saved.locator('[data-receipt-variants-load]').click()
    expect(saved.locator('[data-receipt-field="variant_id"]')).to_have_value('saved')
    expect(saved.locator('[data-receipt-field="package_quantity"]')).to_have_value('900')
    after = page.evaluate("window.App.getRuntimeModule('operation-modal').getEditReceiptPayload()[0]")
    assert after['variant_id'] is None and after['variant_snapshot'] == payload['variant_snapshot']
    saved.locator('[data-receipt-field="quantity"]').fill('3')
    assert page.evaluate("window.App.getRuntimeModule('operation-modal').getEditReceiptPayload()[0].variant_snapshot") == payload['variant_snapshot']
    saved.locator('[data-receipt-field="package_quantity"]').fill('850')
    manual = page.evaluate("window.App.getRuntimeModule('operation-modal').getEditReceiptPayload()[0]")
    assert manual['variant_id'] is None and manual['variant_snapshot'] is None
    expect(saved.locator('[data-receipt-field="variant_id"]')).to_have_value('')
    # Plan editor uses the same historical snapshot, without requesting current defaults.
    page.route('**/api/v1/plans/777', lambda route: route.fulfill(json={
        'id': 777, 'kind': 'expense', 'status': 'upcoming', 'amount': '6.50', 'currency': 'BYN',
        'scheduled_date': '2026-10-13', 'receipt_items': [payload], 'recurrence_enabled': False}))
    page.evaluate("document.getElementById('closeEditModalBtn').click()")
    page.evaluate("window.App.getRuntimeModule('plans').openPlanEdit(777)")
    expect(page.locator('#createTitle')).to_contain_text('Редактировать план')
    plan_row = page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert plan_row['variant_id'] is None and plan_row['variant_snapshot'] == payload['variant_snapshot']
    assert plan_row['package_quantity'] == '900'
    plan_editor_row = page.locator('#receiptItemsList .receipt-item-row').first
    plan_editor_row.locator('[data-receipt-details-toggle]').click()
    plan_editor_row.locator('[data-receipt-field="name"]').fill('Другой товар')
    assert page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0].variant_snapshot") is None
    assert errors == []
