"""Code matching is draft-only, exact, scoped to the store and never changes receipt money."""
import json
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url,page_with_receipt_api_mock
from tests.e2e.test_operation_editor_ux_e2e import open_editor
from tests.e2e.test_receipt_scan_e2e import start,stub,upload

CODE='4006381333931'
FOUND={'product_id':901,'product_name':'Молоко из каталога','name':'Молоко из каталога','template_id':701,'source_id':301,'category_id':101,'brand_id':None,
       'variant_id':41,'variant_snapshot':{'variant_id':41,'name':'900 мл','codes':[CODE]},'sale_unit':'pack','package_quantity':'900.000','package_unit':'ml',
       'matched_by':['barcode'],'matched_codes':[CODE]}
TEXT=f'''ООО ГРИНРОЗНИЦА
№ ДОК 123
Молоко 900 мл
{CODE} 3.10 x2.000 6.20
Скидка -0.20
ИТОГО К ОПЛАТЕ 6.00
13.10.2026 18:24:04'''


def respond(page,items=None,auto=True):
    requests=[]
    def handler(route):
        requests.append(route.request.post_data_json)
        route.fulfill(status=200,content_type='application/json',body=json.dumps({'items':[FOUND] if items is None else items,'auto_match':auto,'warnings':[],'unmatched':[]}))
    page.route('**/api/v1/operations/catalog-products/lookup-codes',handler)
    return requests


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_scan_exact_code_auto_match_preserves_money_and_transfers_variant(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);requests=respond(p);stub(p,TEXT);upload(p);p.click('#scanRun')
    row=p.locator('.scan-row')
    expect(row.locator('.scan-match')).to_contain_text('Найден по штрихкоду')
    expect(row.locator('[data-scan-field=name]')).to_have_value('Молоко из каталога')
    expect(row.locator('[data-scan-field=price]')).to_have_value('3.10')
    expect(row.locator('[data-scan-field=quantity]')).to_have_value('2')
    expect(row.locator('[data-scan-field=discount]')).to_have_value('0.20')
    expect(row.locator('[data-scan-field=total]')).to_have_value('6.00')
    assert requests[0]['shop_name']=='Green' and requests[0]['codes'][0]['code']==CODE
    expect(row.locator('.receipt-code-save')).to_have_count(0)
    expect(row.get_by_role('textbox',name='Код товара',exact=True)).to_be_visible()
    row.locator('.receipt-codes').scroll_into_view_if_needed()
    row.screenshot(path=f'/tmp/fa-scan-code-card-{width}.png')
    p.screenshot(path=f'/tmp/fa-scan-codes-{width}.png')
    assert p.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert item['product_id']==901 and item['variant_id']==41 and item['variant_snapshot']['codes']==[CODE]
    assert float(item['regular_unit_price'])==3.1 and float(item['discount_value'])==.2 and float(item['quantity'])==2
    assert item['catalog_codes']==[{'kind':'barcode','code':CODE}]


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_receipt_compact_codes_selection_registration_and_cancel(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;open_editor(p,static_server_url,width);respond(p)
    p.locator('#createOperationModeSwitch [data-operation-mode=receipt]').click()
    p.locator('[data-receipt-store=create]').fill('Green');p.locator('[data-receipt-store=create]').press('Tab')
    row=p.locator('#receiptItemsList .receipt-item-row').first
    row.locator('[data-receipt-field=name]').fill('Молоко вручную');p.locator('#createTitle').click()
    row.locator('[data-receipt-field=unit_price]').fill('3.10');row.locator('[data-receipt-field=quantity]').fill('2')
    row.locator('[data-receipt-details-toggle]').click()
    row.get_by_role('button',name='Добавить код',exact=True).click()
    field=row.get_by_role('textbox',name='Код товара',exact=True)
    field.fill(CODE);field.press('Enter')
    row.locator('.receipt-code-result').click()
    expect(row.locator('.receipt-compact-name')).to_have_text('Молоко из каталога')
    expect(row.locator('[data-receipt-field=unit_price]')).to_have_value('3.10')
    expect(row.locator('[data-receipt-field=quantity]')).to_have_value('2')
    # Add an unknown SKU explicitly; no catalog write occurs until the receipt is saved.
    writes=[]
    p.on('request',lambda r:writes.append(r.url) if r.method in ['PUT','PATCH','DELETE'] or (r.method=='POST' and not r.url.endswith('/lookup-codes')) else None)
    row.get_by_role('button',name='Ещё код',exact=True).click()
    row.get_by_role('textbox',name='Код товара',exact=True).last.fill('000-42')
    row.get_by_role('combobox',name='Тип кода').last.select_option('retailer')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert payload['catalog_codes']==[{'kind':'barcode','code':CODE},{'kind':'retailer','code':'000-42'}]
    expect(row.locator('[data-receipt-field=category_search]')).to_have_value('Еда')
    row.locator('.receipt-codes').screenshot(path=f'/tmp/fa-code-controls-{width}.png')
    p.screenshot(path=f'/tmp/fa-receipt-codes-{width}.png')
    assert row.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    row.locator('[data-receipt-details-toggle]').click()
    expect(row.locator('.receipt-codes-host')).to_be_visible()
    assert p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")==payload
    p.keyboard.press('Escape')
    assert writes==[]


@pytest.mark.e2e
def test_scan_code_ambiguity_and_shop_change_require_new_choice(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url)
    other={**FOUND,'product_id':902,'product_name':'Другой товар','template_id':702,'variant_id':42}
    requests=respond(p,[FOUND,other],False);stub(p,TEXT);upload(p);p.click('#scanRun')
    row=p.locator('.scan-row')
    expect(row.locator('.receipt-code-result')).to_have_count(2)
    expect(row.locator('[data-scan-field=name]')).to_have_value('Молоко 900 мл')
    row.locator('.receipt-code-result').first.click()
    expect(row.locator('.scan-match')).to_contain_text('Найден по штрихкоду')
    p.locator('#scanShop').fill('Соседи')
    expect(row.locator('.receipt-code-result')).to_have_count(2)
    expect(row.locator('.scan-match')).not_to_contain_text('Найден по штрихкоду')
    assert requests[-1]['shop_name']=='Соседи'


@pytest.mark.e2e
def test_scan_code_package_conflict_requires_explicit_selection(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url);respond(p);stub(p,TEXT.replace('900 мл','1000 мл'));upload(p);p.click('#scanRun')
    row=p.locator('.scan-row')
    expect(row.locator('.receipt-code-result')).to_contain_text('Другая фасовка')
    expect(row.locator('[data-scan-field=name]')).to_have_value('Молоко 1000 мл')
    expect(row.locator('.scan-match')).not_to_contain_text('Найден по штрихкоду')
    row.locator('.receipt-code-result').click()
    expect(row.locator('.scan-match')).to_contain_text('Найден по штрихкоду')


@pytest.mark.e2e
def test_late_code_lookup_cannot_replace_edited_scan_name(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url);pending=[]
    p.route('**/api/v1/operations/catalog-products/lookup-codes',lambda route:pending.append(route))
    stub(p,TEXT);upload(p)
    with p.expect_request(lambda request:request.url.endswith('/lookup-codes')):
        p.click('#scanRun')
    expect(p.locator('#receiptScanDialog .receipt-codes [role=status]')).to_contain_text('Ищу')
    assert pending
    row=p.locator('.scan-row');row.locator('[data-scan-field=name]').fill('Ручное исправление')
    pending[0].fulfill(status=200,content_type='application/json',body=json.dumps({'items':[FOUND],'auto_match':True,'warnings':[],'unmatched':[]}))
    p.wait_for_timeout(100)
    expect(row.locator('[data-scan-field=name]')).to_have_value('Ручное исправление')
    expect(row.locator('.scan-match')).not_to_contain_text('Найден по штрихкоду')


@pytest.mark.e2e
def test_code_can_start_empty_receipt_row_and_adds_trailing_row(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;open_editor(p,static_server_url,390);respond(p)
    p.locator('#createOperationModeSwitch [data-operation-mode=receipt]').click()
    row=p.locator('#receiptItemsList .receipt-item-row').first
    row.locator('[data-receipt-details-toggle]').click();row.get_by_role('button',name='Добавить код',exact=True).click()
    field=row.get_by_role('textbox',name='Код товара',exact=True);field.fill(CODE);field.press('Enter')
    row.locator('.receipt-code-result').click()
    expect(row.locator('.receipt-compact-name')).to_have_text('Молоко из каталога')
    expect(row.locator('[data-receipt-field=quantity]')).to_have_value('1')
    expect(p.locator('#receiptItemsList .receipt-item-row')).to_have_count(2)
    assert float(row.locator('[data-receipt-field=unit_price]').input_value() or 0)==0


@pytest.mark.e2e
def test_saved_store_code_loads_only_when_receipt_details_open(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;open_editor(p,static_server_url,1440);loads=[]
    def identity(route):
        loads.append(route.request.url)
        route.fulfill(json={'variants':[],'offers':[{'template_id':701,'retailer_code':'000-42'}]})
    p.route('**/catalog-products/901/identity',identity)
    p.locator('#createOperationModeSwitch [data-operation-mode=receipt]').click()
    p.evaluate("""()=>{
      const m=window.App.getRuntimeModule('operation-modal');
      window.App.state.createReceiptItems=[m.createReceiptDraft({product_id:901,template_id:701,name:'Молоко',product_name:'Молоко',shop_name:'Green',quantity:1,unit_price:3})];
      m.renderReceiptItems('create');
    }""")
    row=p.locator('#receiptItemsList .receipt-item-row').first
    assert loads==[]
    row.locator('[data-receipt-details-toggle]').click()
    expect(row.locator('input[aria-label="Код товара"]')).to_have_value('000-42')
    expect(row.get_by_role('textbox',name='Код товара',exact=True)).to_be_visible()
    assert len(loads)==1
    assert p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0].catalog_codes")==[]


@pytest.mark.e2e
def test_entered_codes_are_saved_with_operation_and_errors_prevent_writes(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;writes=[]
    def save(route,request):
        if request.method!='POST':return route.fallback()
        data=request.post_data_json;writes.append(data)
        route.fulfill(status=201,json={'id':778,**data,'amount':'3.10','receipt_total':'3.10','receipt_discrepancy':'0.00'})
    p.route('**/api/v1/operations',save)
    open_editor(p,static_server_url,390);respond(p,[],False)
    p.locator('#createOperationModeSwitch [data-operation-mode=receipt]').click()
    p.locator('[data-receipt-store=create]').fill('Green');p.locator('[data-receipt-store=create]').press('Tab')
    row=p.locator('#receiptItemsList .receipt-item-row').first
    row.locator('[data-receipt-field=name]').fill('Молоко вручную');p.locator('#createTitle').click()
    row.locator('[data-receipt-field=unit_price]').fill('3.10');row.locator('[data-receipt-field=quantity]').fill('1')
    row.locator('[data-receipt-details-toggle]').click()
    row.get_by_role('button',name='Добавить код',exact=True).click()
    code=row.get_by_role('textbox',name='Код товара',exact=True)
    code.fill('4006381333932')
    row.locator('[data-receipt-details-toggle]').click()
    p.locator('#submitCreateOperationBtn').click()
    expect(p.locator('#createModal')).to_be_visible()
    expect(row.locator('.receipt-code-error')).to_contain_text('контрольную цифру')
    assert writes==[]
    expect(code).to_be_visible();expect(code).to_be_focused()
    code.fill(CODE)
    row.get_by_role('button',name='Ещё код',exact=True).click()
    row.get_by_role('textbox',name='Код товара',exact=True).last.fill('000-42')
    p.locator('#submitCreateOperationBtn').click()
    expect(p.locator('#createModal')).to_be_hidden()
    assert len(writes)==1
    assert writes[0]['receipt_items'][0]['catalog_codes']==[{'kind':'barcode','code':CODE},{'kind':'retailer','code':'000-42'}]


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
@pytest.mark.parametrize('mode',['create','edit'])
def test_save_conflict_highlights_exact_code_and_selects_owner_without_changing_money(static_server_url,page_with_receipt_api_mock,width,mode):
    p=page_with_receipt_api_mock;writes=[]
    error={'type':'receipt_code_conflict','message':'Штрихкод закреплён за другим товаром или фасовкой','item_index':1,'item_name':'Другое молоко',
           'codes':[{'kind':'barcode','code':CODE}],'owners':[{'kind':'barcode','code':CODE,'product_id':901,'product_name':'Молоко из каталога'}]}
    def save(route,request):
        if request.method not in ('POST','PATCH'):return route.fallback()
        data=request.post_data_json;writes.append(data)
        if len(writes)==1:return route.fulfill(status=400,json={'detail':error})
        route.fulfill(status=201 if mode=='create' else 200,json={'id':777,**data,'amount':'7.50','receipt_total':'7.50','receipt_discrepancy':'0.00'})
    p.route('**/api/v1/operations',save);p.route('**/api/v1/operations/777',save)
    open_editor(p,static_server_url,width);respond(p)
    p.evaluate('''async mode=>{
      const m=window.App.getRuntimeModule('operation-modal');
      const items=[{name:'Первый товар',quantity:1,unit_price:3.1,shop_name:'Green'},
        {name:'Другое молоко',product_name:'Другое молоко',product_id:902,quantity:4,unit_price:1.1,shop_name:'Green',
         code_entries:[{kind:'barcode',code:'4006381333931'},{kind:'retailer',code:'sku-42',manual_kind:true}]}];
      if(mode==='create'){
        window.App.state.createReceiptItems=items.map(item=>m.createReceiptDraft(item));m.setCreateOperationMode('receipt');m.renderReceiptItems('create');m.renderReceiptSummary('create');
      }else{
        window.App.actions.closeCreateModal();await m.openEditModal({id:777,kind:'expense',amount:'7.50',currency:'BYN',operation_date:'2026-10-13',receipt_items:items});
        window.App.state.editReceiptItems=items.map(item=>m.createReceiptDraft(item,'edit'));m.renderReceiptItems('edit');m.renderReceiptSummary('edit');
      }
    }''',mode)
    modal=p.locator(f'#{mode}Modal');row=modal.locator('.receipt-item-row').nth(1)
    fields=row.get_by_role('textbox',name='Код товара',exact=True)
    expect(fields.first).to_be_visible()
    expect(row).to_have_class(__import__('re').compile('is-compact'))
    modal.locator(f'#submit{mode.title()}OperationBtn').click()
    expect(row.locator('.receipt-code-error')).to_contain_text('Молоко из каталога')
    expect(row.locator('.receipt-code-error')).to_contain_text(CODE)
    expect(fields.first).to_have_attribute('aria-invalid','true')
    expect(fields.last).to_have_attribute('aria-invalid','false')
    expect(fields.first).to_be_focused()
    expect(fields.first).to_have_css('outline-color','rgb(238, 127, 139)')
    expect(modal).to_be_visible()
    expect(row.locator('.receipt-code-result')).to_be_visible()
    assert row.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    row.screenshot(path=f'/tmp/fa-code-conflict-{mode}-{width}.png')
    row.locator('.receipt-code-result').click()
    expect(row.locator('.receipt-code-error')).to_be_hidden()
    expect(row.locator('.receipt-compact-name')).to_have_text('Молоко из каталога')
    expect(row.locator('[data-receipt-field=quantity]')).to_have_value('4')
    expect(row.locator('[data-receipt-field=unit_price]')).to_have_value('1.10')
    modal.locator(f'#submit{mode.title()}OperationBtn').click()
    p.wait_for_function('mode=>!document.querySelector(`#submit${mode[0].toUpperCase()+mode.slice(1)}OperationBtn`).disabled',arg=mode)
    assert len(writes)==2
    before,after=writes[0]['receipt_items'][1],writes[1]['receipt_items'][1]
    assert after['product_id']==901
    for key in ['quantity','unit_price','discount_mode','discount_value','is_discounted']:
        assert before.get(key)==after.get(key)


@pytest.mark.e2e
def test_late_save_conflict_does_not_highlight_corrected_code(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;pending=[]
    p.route('**/api/v1/operations',lambda route:pending.append(route) if route.request.method=='POST' else route.fallback())
    open_editor(p,static_server_url,390);respond(p,[],False)
    p.evaluate('''()=>{
      const m=window.App.getRuntimeModule('operation-modal');
      window.App.state.createReceiptItems=[m.createReceiptDraft({name:'Молоко',quantity:1,unit_price:3.1,shop_name:'Green',code_entries:[{kind:'barcode',code:'4006381333931'}]})];
      m.setCreateOperationMode('receipt');m.renderReceiptItems('create');m.renderReceiptSummary('create');
    }''')
    with p.expect_request(lambda r:r.url.endswith('/operations') and r.method=='POST'):
        p.locator('#submitCreateOperationBtn').click()
    row=p.locator('#receiptItemsList .receipt-item-row').first
    field=row.get_by_role('textbox',name='Код товара',exact=True)
    field.fill('4811040140757')
    pending[0].fulfill(status=400,json={'detail':{'type':'receipt_code_conflict','message':'Штрихкод закреплён за другим товаром',
        'item_index':0,'item_name':'Молоко','codes':[{'kind':'barcode','code':CODE}],'owners':[]}})
    expect(p.locator('#submitCreateOperationBtn')).to_be_enabled()
    expect(p.locator('#createModal')).to_be_visible()
    expect(field).to_have_value('4811040140757')
    expect(field).to_have_attribute('aria-invalid','false')
    expect(row.locator('.receipt-code-error')).to_be_hidden()
