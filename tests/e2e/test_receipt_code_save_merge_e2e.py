import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url,page_with_receipt_api_mock
from tests.e2e.test_receipt_scan_e2e import start,stub,upload
from tests.e2e.test_receipt_codes_e2e import TEXT,FOUND,respond

REPEATS='000 "ЕВРОТОРГ"\n№ ДОК\n2186323 Пельмени Бульварские\nслив. масл. 430г 4811040140757\n5.99 x1.000 5.99\n'+('1751767 Сырок Ясь Белоус\nфундук-какао 16% 45г 4810729017151\n1.10 x1.000 1.10\n'*4)+'ИТОГО К ОПЛАТЕ 10.39\n15.10.2026 21:23:00'


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_codes_save_with_receipt_and_invalid_barcode_blocks_transfer(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);respond(p,[],False)
    stub(p,TEXT.replace('Молоко 900 мл','2186323 Молоко 900 мл'));upload(p);p.click('#scanRun')
    row=p.locator('.scan-row');hint=row.locator('.receipt-code-error')
    expect(row.locator('.receipt-code-save')).to_have_count(0)
    expect(row.get_by_role('combobox',name='Тип кода').first).to_have_value('retailer')
    field=row.get_by_role('textbox',name='Код товара',exact=True).last
    field.fill('4006381333932')
    expect(hint).to_contain_text('Проверьте длину и контрольную цифру')
    p.locator('#scanConfirmed').check();expect(p.locator('#scanTransfer')).to_be_disabled()
    field.fill('4006381333931');expect(hint).to_be_hidden()
    row.locator('[data-scan-unit=pack]').click()
    row.locator('.receipt-codes').screenshot(path=f'/tmp/fa-auto-code-save-{width}.png')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert item['catalog_codes']==[{'kind':'retailer','code':'2186323'},{'kind':'barcode','code':'4006381333931'}]


@pytest.mark.e2e
def test_pending_auto_lookup_cannot_replace_manually_edited_code(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url);pending=[]
    p.route('**/catalog-products/lookup-codes',lambda r:pending.append(r))
    stub(p,TEXT);upload(p)
    with p.expect_request(lambda r:r.url.endswith('/lookup-codes')):p.click('#scanRun')
    row=p.locator('.scan-row');field=row.get_by_role('textbox',name='Код товара',exact=True)
    field.fill('4811040140757')
    pending[0].fulfill(json={'items':[FOUND],'auto_match':True,'warnings':[],'unmatched':[]})
    expect(field).to_have_value('4811040140757')
    expect(row.locator('[data-scan-field=name]')).to_have_value('Молоко 900 мл')
    expect(row.locator('.receipt-code-save')).to_have_count(0)


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_merge_four_barcoded_items_preserves_receipt_total_and_transfer(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);respond(p,[],False)
    stub(p,REPEATS);upload(p);p.click('#scanRun')
    expect(p.locator('.scan-row')).to_have_count(2)
    expect(p.locator('#scanMergeDuplicates')).to_have_count(0)
    row=p.locator('.scan-row').last
    expect(row.locator('[data-scan-field=quantity]')).to_have_value('4')
    expect(row.locator('[data-scan-field=price]')).to_have_value('1.10')
    expect(row.locator('[data-scan-field=total]')).to_have_value('4.40')
    expect(row.locator('.scan-merged-note')).to_have_count(0)
    expect(row.locator('.scan-row-actions [data-scan-split]')).to_be_visible()
    expect(p.locator('#scanTotal')).to_have_value('10.39')
    row.scroll_into_view_if_needed();p.screenshot(path=f'/tmp/fa-merged-receipt-{width}.png')
    assert p.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    items=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert all(not item.get('note') for item in items)
    assert len(items)==2 and items[1]['quantity']=='4' and float(items[1]['unit_price'])==1.1
    expect(p.locator('#opAmount')).to_have_value('10.39')


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_automatic_merge_can_split_without_remerging_or_losing_catalog_edits(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);respond(p,[],False)
    stub(p,REPEATS);upload(p);p.click('#scanRun')
    expect(p.locator('.scan-row')).to_have_count(2)
    row=p.locator('.scan-row').last
    row.locator('[data-scan-category]').select_option('101')
    row.locator('[data-scan-unit=pack]').click()
    row.get_by_role('combobox',name='Тип кода').first.select_option('retailer')
    p.locator('#scanConfirmed').check()
    row.locator('[data-scan-split]').click()
    expect(p.locator('.scan-row')).to_have_count(5)
    expect(p.locator('#scanConfirmed')).not_to_be_checked()
    expect(p.locator('[data-scan-split]')).to_have_count(0)
    for restored in p.locator('.scan-row').all()[1:]:
        expect(restored.locator('[data-scan-field=quantity]')).to_have_value('1')
        expect(restored.locator('[data-scan-field=total]')).to_have_value('1.10')
        expect(restored.locator('[data-scan-category]')).to_have_value('101')
        expect(restored.locator('[data-scan-unit=pack]')).to_have_attribute('aria-pressed','true')
        expect(restored.get_by_role('combobox',name='Тип кода').first).to_have_value('retailer')
    # Editing a split row and unrelated metadata must not group the rows again.
    p.locator('.scan-row').nth(1).locator('[data-scan-field=name]').fill('Сырок вручную')
    p.locator('#scanDate').fill('2026-10-14')
    expect(p.locator('.scan-row')).to_have_count(5)
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    items=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert len(items)==5 and all(r['quantity']=='1' for r in items)
    assert items[2]['category_id']==101 and items[2]['catalog_codes']
    expect(p.locator('#opAmount')).to_have_value('10.39')


@pytest.mark.e2e
def test_split_modified_money_explains_restore_and_cancel_preserves_edits(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url,390);respond(p,[],False)
    stub(p,REPEATS);upload(p);p.click('#scanRun')
    row=p.locator('.scan-row').last
    row.locator('[data-scan-field=quantity]').fill('3')
    row.locator('[data-scan-split]').click()
    expect(row.locator('.scan-split-confirm')).to_be_visible()
    expect(row.locator('.scan-split-confirm')).to_contain_text('Восстановить количество, цены и скидки')
    row.get_by_role('button',name='Отмена',exact=True).click()
    expect(row.locator('.scan-split-confirm')).to_be_hidden()
    expect(row.locator('[data-scan-field=quantity]')).to_have_value('3')
    row.locator('[data-scan-split]').click()
    row.locator('.scan-split-confirm').screenshot(path='/tmp/fa-auto-merge-split-confirm.png')
    row.get_by_role('button',name='Вернуть строки из чека',exact=True).click()
    expect(p.locator('.scan-row')).to_have_count(5)
    expect(p.locator('#scanArithmetic')).to_contain_text('Суммы сходятся')


@pytest.mark.e2e
def test_split_restores_interleaved_receipt_order_and_reparse_groups_again(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url);respond(p,[],False)
    text='ООО Тест\n№ ДОК\nСырок\n4810729017151 1.10 x1.000 1.10\nПельмени\n4811040140757 5.99 x1.000 5.99\nСырок\n4810729017151 1.10 x1.000 1.10\nИТОГО К ОПЛАТЕ 8.19\n15.10.2026 21:23:00'
    stub(p,text);upload(p);p.click('#scanRun')
    expect(p.locator('.scan-row')).to_have_count(2)
    p.locator('[data-scan-split]').click()
    expect(p.locator('.scan-row')).to_have_count(3)
    assert p.locator('[data-scan-field=name]').evaluate_all('nodes=>nodes.map(n=>n.value)')==['Сырок','Пельмени','Сырок']
    p.click('#scanShowText');p.click('#scanReparse')
    expect(p.locator('.scan-row')).to_have_count(2)
    expect(p.locator('[data-scan-split]')).to_have_count(1)


@pytest.mark.e2e
def test_merged_quantity_is_the_only_multiplier_when_edited(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url);respond(p,[],False)
    stub(p,REPEATS);upload(p);p.click('#scanRun')
    row=p.locator('.scan-row').last
    row.locator('[data-scan-field=quantity]').fill('3')
    expect(row.locator('[data-scan-field=total]')).to_have_value('3.30')
    p.locator('#scanTotal').fill('9.29');p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[1]")
    assert item['quantity']=='3' and float(item['unit_price'])==1.1
    assert 'merged_count' not in item and 'merged_rows' not in item
    expect(p.locator('#opAmount')).to_have_value('9.29')


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1440])
def test_internal_code_is_accepted_without_workarounds_or_money_changes(static_server_url,page_with_receipt_api_mock,width,tmp_path):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);respond(p,[],False)
    text='ООО ГРИНРОЗНИЦА\n№ ДОК 118861\nЛук репчатый красный вес\n22373102227750 3.66 x0.370 1.35\nИТОГО К ОПЛАТЕ 1.35\n22.10.2026 20:33:06'
    stub(p,text);upload(p);p.click('#scanRun')
    row=p.locator('.scan-row');button=row.locator('[data-receipt-code-as-retailer]')
    expect(row.get_by_role('combobox',name='Тип кода')).to_have_value('internal')
    expect(row.get_by_role('textbox',name='Код товара',exact=True)).to_have_value('22373102227750')
    expect(row.locator('.receipt-code-error')).to_be_hidden()
    expect(button).to_have_count(0)
    row.locator('[data-scan-unit=kg]').click()
    p.locator('#scanConfirmed').check();expect(p.locator('#scanTransfer')).to_be_enabled()
    row.screenshot(path=str(tmp_path/f'internal-code-{width}.png'))
    p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert item['catalog_codes']==[{'kind':'internal','code':'22373102227750'}]
    assert item['receipt_codes']==item['catalog_codes']
    assert float(item['quantity'])==.37 and float(item['unit_price'])==3.66
    expect(p.locator('#opAmount')).to_have_value('1.35')


@pytest.mark.e2e
def test_saved_internal_code_reopens_with_stable_catalog_sku(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url,1440);respond(p,[],False)
    result=p.evaluate("""()=>{
      const modal=window.App.getRuntimeModule('operation-modal');
      const row=modal.createReceiptDraft({name:'Лук',shop_name:'Green',quantity:.37,unit_price:3.66,
        receipt_codes:[{kind:'retailer',code:'22373102227750'}]});
      row.code_entries.push({kind:'retailer',code:'1582951',from_catalog:true});
      return {codes:row.code_entries,payload:window.App.receiptCodes.payload(row),receipt:window.App.receiptCodes.receiptPayload(row),error:window.App.receiptCodes.validationError(window.App.receiptCodes.payload(row),'Green')};
    }""")
    assert len(result['codes'])==2
    assert result['payload']==[]
    assert result['receipt']==[{'kind':'internal','code':'22373102227750'}]
    assert not result['error']


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1440])
def test_repeat_internal_code_auto_selects_catalog_product_without_changing_money(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width)
    found={**FOUND,'name':'Лук красный','product_name':'Лук красный','sale_unit':'kg','package_quantity':None,'package_unit':None,
           'variant_id':None,'variant_snapshot':None,'matched_by':['internal'],'matched_codes':['22373102227750']}
    requests=respond(p,[found],True)
    text='ООО ГРИНРОЗНИЦА\n№ ДОК 118861\nЛук репчатый красный вес\n22373102227750 3.66 x0.370 1.35\nИТОГО К ОПЛАТЕ 1.35\n22.10.2026 20:33:06'
    stub(p,text);upload(p);p.click('#scanRun')
    row=p.locator('.scan-row')
    expect(row.locator('.scan-match')).to_contain_text('Найден по внутреннему штрихкоду')
    assert requests[0]['shop_name']=='Green'
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert item['product_id']==901 and item['template_id']==701
    assert float(item['quantity'])==.37 and float(item['unit_price'])==3.66
    expect(p.locator('#opAmount')).to_have_value('1.35')
