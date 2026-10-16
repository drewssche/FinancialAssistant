import pytest
from playwright.sync_api import expect
from tests.e2e.test_product_primary_codes_e2e import setup, card, barcode
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url,page_with_receipt_api_mock,_login,_ensure_categories_loaded


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_source_size_inherits_overrides_and_saves_without_moving_barcode(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,width,many=True)
    p.locator('[data-product-tab=offers]').click()
    a=card(p);b=card(p,502)
    expect(a.locator('[data-offer-own-size]')).not_to_be_checked()
    a.locator('[data-offer-own-size]').check()
    a.locator('[data-offer-size-field=package_quantity]').fill('200')
    a.locator('[data-offer-size-field=package_quantity]').press('Tab')
    expect(barcode(p)).to_have_value('');expect(barcode(p,502)).to_have_value('4006381333931')
    barcode(p).fill('5901234123457')
    p.locator('[data-product-tab=product]').click()
    p.locator('#catalogProductForm .measurement-editor input').fill('800')
    p.locator('#catalogProductForm .measurement-editor input').press('Tab')
    p.locator('[data-product-tab=offers]').click()
    expect(a.locator('[data-offer-size-field=package_quantity]')).to_have_value('200')
    expect(b.locator('.offer-source-size')).to_contain_text('800')
    a.scroll_into_view_if_needed();p.screenshot(path=f'/tmp/fa-source-size-{width}.png')
    for field in a.locator('[data-offer-size-field]').all():
        box=field.bounding_box();assert box['x']>=0 and box['x']+box['width']<=width+1
    p.locator('#submitCatalogProductBtn').click();expect(p.locator('#catalogProductModal')).to_be_hidden()
    own=writes[-1]['codes']['offer_sizes'][0]
    assert own['template_id']==501 and own['use_product_size'] is False and float(own['package_quantity'])==200
    assert own['codes']==['5901234123457']


@pytest.mark.e2e
def test_source_size_reset_and_cancel(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,390)
    p.locator('[data-product-tab=offers]').click();a=card(p)
    a.locator('[data-offer-own-size]').check()
    a.locator('[data-offer-size-field=package_quantity]').fill('200');a.locator('[data-offer-size-field=package_quantity]').press('Tab')
    a.locator('[data-offer-own-size]').uncheck();expect(a.locator('[data-offer-size-field]')).to_have_count(0)
    expect(barcode(p)).to_have_value('4006381333931')
    p.locator('#closeCatalogProductModalBtn').click();assert writes==[]
    p.evaluate("window.App.getRuntimeModule('catalog-products').openEditor(401)")
    p.locator('[data-product-tab=offers]').click();expect(a.locator('[data-offer-own-size]')).not_to_be_checked()


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_scan_is_visible_before_choosing_receipt_mode(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;p.set_viewport_size({'width':width,'height':1000})
    p.goto(static_server_url+'/static/index.html');_login(p);_ensure_categories_loaded(p)
    p.locator('#addOperationCta').click()
    button=p.locator('#openReceiptScan')
    expect(button).to_be_visible();expect(button).to_contain_text('Сканировать чек');expect(button).to_contain_text('буфера')
    expect(p.locator('#opOperationMode')).to_have_value('common')
    assert button.bounding_box()['y']<p.locator('#createOperationForm').bounding_box()['y']
    p.screenshot(path=f'/tmp/fa-scan-entry-{width}.png')
    button.click();expect(p.locator('#receiptScanDialog')).to_be_visible()
    p.locator('#scanClose').click();expect(p.locator('#opOperationMode')).to_have_value('common')
    p.locator('[data-entry-mode=currency]').click();expect(button).to_be_hidden()
    p.locator('[data-entry-mode=operation]').click();expect(button).to_be_visible()


@pytest.mark.e2e
def test_scan_catalog_selection_uses_source_size_and_preserves_paid_price(static_server_url,page_with_receipt_api_mock):
    from tests.e2e.test_receipt_scan_e2e import start,stub,upload
    from tests.e2e.test_receipt_scan_catalog_e2e import seed_catalog,PIZZA
    p=page_with_receipt_api_mock;start(p,static_server_url);seed_catalog(p)
    p.evaluate("""() => {
      const product=window.App.state.receiptProductHints[0];
      Object.assign(product,{sale_unit:'pack',package_quantity:900,package_unit:'g'});
      Object.assign(product.offers[0],{measurement_source:'offer',sale_unit:'pack',package_quantity:200,package_unit:'g',variant_id:55});
    }""")
    stub(p,PIZZA);upload(p);p.click('#scanRun')
    p.locator('.scan-row .scan-suggestion').first.click()
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    row=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert row['variant_id']==55 and float(row['package_quantity'])==200 and row['package_unit']=='g'
    assert row['template_id']==701 and float(row['unit_price'])==4.99
