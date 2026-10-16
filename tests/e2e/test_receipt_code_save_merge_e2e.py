import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url,page_with_receipt_api_mock
from tests.e2e.test_receipt_scan_e2e import start,stub,upload
from tests.e2e.test_receipt_codes_e2e import TEXT,FOUND,respond

REPEATS='000 "ЕВРОТОРГ"\n№ ДОК\n2186323 Пельмени Бульварские\nслив. масл. 430г 4811040140757\n5.99 x1.000 5.99\n'+('1751767 Сырок Ясь Белоус\nфундук-какао 16% 45г 4810729017151\n1.10 x1.000 1.10\n'*4)+'ИТОГО К ОПЛАТЕ 10.39\n15.10.2026 21:23:00'


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_save_codes_explains_unrecognized_type_and_syncs_after_unit_change(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);respond(p,[],False)
    stub(p,TEXT.replace('Молоко 900 мл','2186323 Молоко 900 мл'));upload(p);p.click('#scanRun')
    row=p.locator('.scan-row');save=row.locator('.receipt-code-save input');hint=row.locator('.receipt-code-save-hint')
    expect(save).to_be_disabled();expect(hint).to_contain_text('Для кода 2186323 выберите тип')
    row.get_by_role('combobox',name='Тип кода').first.select_option('retailer')
    expect(save).to_be_enabled();save.check();expect(hint).to_contain_text('вместе с сохранением операции')
    save.uncheck();expect(save).not_to_be_checked();save.check()
    row.locator('[data-scan-unit=pack]').click();expect(save).not_to_be_checked()
    save.check();row.locator('.receipt-codes').screenshot(path=f'/tmp/fa-code-save-{width}.png')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert item['catalog_codes']==[{'kind':'retailer','code':'2186323'},{'kind':'barcode','code':'4006381333931'}]


@pytest.mark.e2e
def test_pending_auto_lookup_cannot_reset_explicit_save_choice(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url);pending=[]
    p.route('**/catalog-products/lookup-codes',lambda r:pending.append(r))
    stub(p,TEXT);upload(p)
    with p.expect_request(lambda r:r.url.endswith('/lookup-codes')):p.click('#scanRun')
    row=p.locator('.scan-row');save=row.locator('.receipt-code-save input')
    expect(save).to_be_enabled();save.check()
    pending[0].fulfill(json={'items':[FOUND],'auto_match':True,'warnings':[],'unmatched':[]})
    p.wait_for_timeout(100)
    expect(save).to_be_checked();expect(row.locator('[data-scan-field=name]')).to_have_value('Молоко 900 мл')
    save.uncheck();expect(save).not_to_be_checked()


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_merge_four_barcoded_items_preserves_receipt_total_and_transfer(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);respond(p,[],False)
    stub(p,REPEATS);upload(p);p.click('#scanRun')
    expect(p.locator('.scan-row')).to_have_count(5)
    merge=p.locator('#scanMergeDuplicates');expect(merge).to_have_text('Объединить повторы · 5 → 2')
    p.locator('#scanConfirmed').check();merge.click()
    expect(p.locator('#scanConfirmed')).not_to_be_checked()
    expect(p.locator('.scan-row')).to_have_count(2);expect(merge).to_be_hidden()
    row=p.locator('.scan-row').last
    expect(row.locator('[data-scan-field=quantity]')).to_have_value('4')
    expect(row.locator('[data-scan-field=price]')).to_have_value('1.10')
    expect(row.locator('[data-scan-field=total]')).to_have_value('4.40')
    expect(row.locator('.scan-merged-note')).to_contain_text('4')
    expect(p.locator('#scanTotal')).to_have_value('10.39')
    row.scroll_into_view_if_needed();p.screenshot(path=f'/tmp/fa-merged-receipt-{width}.png')
    assert p.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    items=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert len(items)==2 and items[1]['quantity']=='4' and float(items[1]['unit_price'])==1.1
    expect(p.locator('#opAmount')).to_have_value('10.39')
