from decimal import Decimal

import pytest
from playwright.sync_api import expect

from tests.e2e.test_receipt_picker_store_scope_e2e import (
    static_server_url, page_with_receipt_api_mock, _login, _ensure_categories_loaded,
)


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1440])
def test_weighted_line_discount_modes_and_edit_roundtrip(static_server_url, page_with_receipt_api_mock, width):
    page = page_with_receipt_api_mock
    page.set_viewport_size({'width': width, 'height': 1100})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(f'{static_server_url}/static/index.html')
    page.evaluate("() => { window.Telegram = {WebApp: {initData: 'mock-init-data', ready() {}, expand() {}}}; }")
    _login(page)
    _ensure_categories_loaded(page)
    page.click('#addOperationCta')
    page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
    row = page.locator('#receiptItemsList .receipt-item-row').first
    row.locator('[data-receipt-field="name"]').fill('Сыр весовой тестовый')
    page.locator('#createTitle').click()  # Finish name entry and dismiss its suggestions.
    row.locator('[data-receipt-field="quantity"]').fill('0.242')
    row.locator('[data-receipt-field="unit_price"]').fill('15.64')
    row.locator('[data-receipt-discount-toggle]').click()
    expect(row.locator('[data-receipt-details-toggle]')).to_have_attribute('aria-expanded', 'false')
    expect(row.locator('.receipt-discount-type-row')).to_be_visible()
    row.locator('[data-receipt-discount-type="coupon"]').click()
    expect(row.locator('[data-receipt-discount-type="coupon"]')).to_have_attribute('aria-pressed', 'true')
    row.locator('[data-receipt-field="regular_unit_price"]').fill('15.64')
    row.locator('[data-receipt-field="discount_mode"]').select_option('amount')
    row.locator('[data-receipt-field="discount_value"]').fill('0.13')
    expect(row.locator('.receipt-line-total strong')).to_contain_text('3,65')
    expect(row.locator('[data-receipt-field="unit_price"]')).to_have_attribute('readonly', '')
    payload = page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert payload['discount_mode'] == 'amount'
    assert payload['discount_type'] == 'coupon'
    assert Decimal(payload['discount_value']) == Decimal('0.13')
    assert abs(Decimal(payload['unit_price']) - Decimal('3.65') / Decimal('0.242')) < Decimal('0.000001')
    # FX settlement and preview must use the exact line total as well.
    expect(page.locator('#createPreviewBody')).to_contain_text('3,65')
    row.locator('[data-receipt-field="discount_mode"]').select_option('percent')
    row.locator('[data-receipt-field="discount_value"]').fill('10')
    expect(row.locator('.receipt-line-total strong')).to_contain_text('3,40')
    row.locator('[data-receipt-field="quantity"]').fill('0.484')
    expect(row.locator('.receipt-line-total strong')).to_contain_text('6,81')
    row.locator('[data-receipt-field="discount_mode"]').select_option('final')
    row.locator('[data-receipt-field="discount_value"]').fill('3.65')
    row.locator('[data-receipt-field="quantity"]').fill('0.242')
    expect(row.locator('.receipt-line-total strong')).to_contain_text('3,65')
    expect(row.locator('.receipt-pricing-explanation')).to_contain_text('введённый итог сохраняется')
    payload = page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    for control in row.locator('.receipt-discount-calculation input, .receipt-discount-calculation select').all():
        box = control.bounding_box()
        assert box['x'] >= 0
        assert box['x'] + box['width'] <= width
    page.screenshot(path=f'/tmp/fa-discounts-receipt-{width}.png', full_page=True)
    page.evaluate('''async (receipt) => {
      window.App.actions.closeCreateModal();
      await window.App.getRuntimeModule('operation-modal').openEditModal({
        id: 777, kind: 'expense', amount: '3.65', original_amount: '3.65', currency: 'BYN',
        operation_date: '2026-10-12', receipt_items: [{...receipt, template_id: 1}]
      });
    }''', payload)
    saved = page.locator('#editReceiptItemsList .receipt-item-row').first
    expect(saved.locator('[data-receipt-field="discount_mode"]')).to_have_value('final')
    expect(saved.locator('.receipt-line-total strong')).to_contain_text('3,65')
    after = page.evaluate("window.App.getRuntimeModule('operation-modal').getEditReceiptPayload()[0]")
    assert Decimal(after['discount_value']) == Decimal('3.65')
    saved.locator('[data-receipt-discount-toggle]').click()
    expect(saved.locator('[data-receipt-details-toggle]')).to_have_attribute('aria-expanded', 'false')
    expect(saved.locator('[data-receipt-discount-type="coupon"]')).to_have_attribute('aria-pressed', 'true')
    saved.locator('[data-receipt-discount-type="loyalty_points"]').click()
    expect(saved.locator('[data-receipt-discount-type="loyalty_points"]')).to_have_attribute('aria-pressed', 'true')
    assert page.evaluate("window.App.getRuntimeModule('operation-modal').getEditReceiptPayload()[0].discount_type") == 'loyalty_points'
    expect(saved.locator('.receipt-line-total strong')).to_contain_text('3,65')
    saved.locator('.receipt-discount-type-row').screenshot(path=f'/tmp/fa-discount-types-{width}.png')
    # Removing known original price must keep the exact final, without guessing savings.
    saved.locator('[data-receipt-field="regular_unit_price"]').fill('')
    expect(saved.locator('.receipt-pricing-explanation')).to_contain_text('неизвестна')
    expect(saved.locator('.receipt-line-total strong')).to_contain_text('3,65')
    # Invalid discount stays visible/in payload, never silently drops the receipt line.
    saved.locator('[data-receipt-field="discount_mode"]').select_option('amount')
    expect(saved.locator('.receipt-pricing-explanation')).to_contain_text('Укажите цену')
    assert len(page.evaluate("window.App.getRuntimeModule('operation-modal').getEditReceiptPayload()")) == 1
    tiny = page.evaluate("""() => window.App.getRuntimeModule('operation-modal').createReceiptDraft({
      name: 'Малая эффективная цена', quantity: '100', unit_price: '0.0001',
      is_discounted: true, discount_mode: 'final', discount_value: '0.01'
    })""")
    assert Decimal(str(tiny['unit_price'])) == Decimal('0.0001')
    assert errors == []
