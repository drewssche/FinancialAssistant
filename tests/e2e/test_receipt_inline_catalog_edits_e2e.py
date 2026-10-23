import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock
from tests.e2e.test_receipt_scan_e2e import start, stub, upload
from tests.e2e.test_receipt_scan_catalog_e2e import seed_catalog, PIZZA


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1440])
def test_edit_linked_scan_fields_keeps_identity_and_money_until_operation_save(static_server_url,page_with_receipt_api_mock,width,tmp_path):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);seed_catalog(p)
    p.evaluate('''()=>{window.App.state.itemBrands=[{id:8701,name:'Новый бренд'}];window.App.state.itemBrandsLoaded=true;}''')
    writes=[]
    p.on('request',lambda r:writes.append(r.url) if r.method in ['PATCH','PUT','POST'] and ('catalog-products' in r.url or r.url.endswith('/operations')) else None)
    stub(p,PIZZA);upload(p);p.click('#scanRun')
    row=p.locator('.scan-row').first;name=row.locator('[data-scan-field=name]')
    name.focus();row.locator('.receipt-template-suggestion').first.click()
    name.fill('Пицца Черри-чеддер новая 180г')
    expect(row.locator('.scan-match')).to_contain_text('Из каталога')
    row.locator('[data-scan-unit="pack"]').click()
    # The same shared measurement editor is used by catalogue and receipt forms.
    row.get_by_role('spinbutton',name='Размер одной упаковки').fill('180')
    row.locator('.measurement-size [data-unit="g"]').click()
    brand=row.locator('[data-scan-brand]')
    brand.click();p.locator('#appChoiceDialog').get_by_role('button',name='Новый бренд',exact=True).click()
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert payload['product_id']==901 and payload['template_id']==701
    assert payload['name']=='Пицца Черри-чеддер новая 180г'
    assert payload['catalog_name_touched'] and payload['catalog_measurement_touched']
    assert payload['sale_unit']=='pack' and float(payload['package_quantity'])==180 and payload['package_unit']=='g'
    assert payload['brand_id']==8701 and float(payload['unit_price'])==4.99 and float(payload['quantity'])==1
    assert not writes
    operation_row=p.locator('#createModal .receipt-item-row').first
    operation_row.locator('[data-receipt-details-toggle]').click()
    operation_row.locator('[data-receipt-field=name]').fill('Пицца исправленная 180г')
    operation_row.locator('[data-receipt-field=name]').press('Escape')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert payload['product_id']==901 and payload['template_id']==701 and payload['catalog_name_touched']
    assert payload['name']=='Пицца исправленная 180г' and payload['catalog_measurement_touched']
    p.click('#openReceiptScan')
    expect(p.locator('[data-scan-field=name]').first).to_have_value(payload['name'])
    expect(p.locator('[data-scan-brand]').first).to_have_value('8701')
    assert p.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    p.screenshot(path=str(tmp_path/f'inline-catalog-{width}.png'))
