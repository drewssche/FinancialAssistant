import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url,page_with_receipt_api_mock
from tests.e2e.test_receipt_scan_e2e import start,stub,upload
from tests.e2e.test_product_primary_codes_e2e import setup
from tests.e2e.modal_layout_assertions import assert_controls_fit,assert_text_fits


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,400,401,641,800,1440])
def test_populated_receipt_catalog_and_nested_dialog_controls(static_server_url,page_with_receipt_api_mock,width,tmp_path):
    p=page_with_receipt_api_mock
    start(p,static_server_url,width);stub(p);upload(p);p.click('#scanRun')
    expect(p.locator('#scanReview')).to_be_visible()
    assert_controls_fit(p.locator('#receiptScanDialog'))
    p.click('#scanShowText')
    assert_controls_fit(p.locator('#scanTextDialog'))
    p.locator('#scanText').fill(p.locator('#scanText').input_value())
    p.click('#scanTextClose')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    row=p.locator('#receiptItemsList .receipt-item-row').first
    row.locator('[data-receipt-details-toggle]').click();row.locator('[data-receipt-discount-toggle]').click()
    assert_controls_fit(p.locator('#createModal'))
    if width<=400:
        assert_text_fits(row.locator('[data-receipt-field=category_search]'),'Выбрать категорию')
        assert_text_fits(row.locator('[data-receipt-field=unit_price]'),'12345.67')
        assert_text_fits(row.locator('[data-receipt-field=quantity]'),'0.375')
    # Controls near the bottom remain reachable above the sticky save action.
    row.locator('[data-receipt-field=regular_unit_price]').click(trial=True)
    p.locator('#submitCreateOperationBtn').click(trial=True)
    row.scroll_into_view_if_needed()
    p.screenshot(path=str(tmp_path/f'receipt-{width}.png'))
    p.evaluate("window.App.getRuntimeModule('operation-modal').openCreateModal()")
    p.locator('#opCurrency').select_option('USD')
    assert_controls_fit(p.locator('#createModal'))
    p.locator('#opCurrency').select_option('BYN')
    p.locator('#createModal button[aria-label="Валютный остаток"]').click()
    assert_controls_fit(p.locator('#createModal .task-dialog'))
    p.locator('#createModal .task-dialog').get_by_role('button',name='Закрыть настройки').click()
    p.locator('#opCurrency').click()
    expect(p.locator('#appChoiceDialog')).to_be_visible()
    assert_controls_fit(p.locator('#appChoiceDialog'))
    p.locator('#appChoiceDialog .choice-option').filter(has_text='EUR').click()
    expect(p.locator('#opCurrency')).to_have_value('EUR')
    setup(p,static_server_url,width,many=True)
    for tab in ['product','offers','prices','purchases']:
        p.locator(f'[data-product-tab="{tab}"]').click()
        assert_controls_fit(p.locator('#catalogProductModal'))
    p.screenshot(path=str(tmp_path/f'catalog-{width}.png'))
