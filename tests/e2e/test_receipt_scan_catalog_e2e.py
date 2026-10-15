"""Catalog selection must preserve receipt money and require an explicit identity choice."""
import base64
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock
from tests.e2e.test_receipt_scan_e2e import start, stub, upload, image

PIZZA='''ООО Соседи
№ ДОК 1
ПИЦЦА КУСОК ЧЕРРИ ЧЕДЕР 200Г
4.99 x1.000 4.99
ИТОГО К ОПЛАТЕ 4.99
13.10.2026 22:53:51'''

def seed_catalog(page):
    page.evaluate('''async()=>{
      await window.App.getRuntimeModule('operation-modal').receiptCatalog.load();
      window.App.state.receiptTemplateHints=[];
      window.App.state.receiptProductHints=[
        {id:901,name:'Пицца Черри-чеддер 200г',category_id:101,offers:[
          {id:701,template_id:701,source_id:301,shop_name:'Соседи',name:'Пицца-кусок черри-чеддер 200г',latest_unit_price:99},
          {id:702,template_id:702,source_id:302,shop_name:'Green',name:'Пицца черри чеддер',latest_unit_price:88}]},
        {id:902,name:'Пицца Грибной цыплёнок 200г',category_id:101,offers:[
          {id:703,template_id:703,source_id:301,shop_name:'Соседи',name:'Пицца-кусок грибной цыплёнок 200г',latest_unit_price:77}]}
      ];
    }''')

@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_catalog_suggestion_preserves_money_and_identity_on_transfer(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);seed_catalog(p);stub(p,PIZZA);upload(p);p.click('#scanRun')
    row=p.locator('.scan-row').first
    expect(row.locator('.scan-suggestion').first).to_contain_text('Черри-чеддер')
    assert p.evaluate('window.App.state.createReceiptItems.every(r=>!r.product_id)')
    row.locator('.scan-suggestion').first.click()
    expect(row.locator('[data-scan-field=price]')).to_have_value('4.99')
    expect(row.locator('[data-scan-field=total]')).to_have_value('4.99')
    expect(row.locator('.scan-match')).to_contain_text('Из каталога')
    p.screenshot(path=f'/tmp/fa-scan-catalog-{width}.png')
    assert p.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert len(payload)==1 and payload[0]['product_id']==901 and payload[0]['template_id']==701
    assert payload[0]['source_id']==301 and payload[0]['category_id']==101
    assert float(payload[0]['unit_price'])==4.99 and payload[0]['package_unit'] is None

@pytest.mark.e2e
def test_manual_row_search_keyboard_and_change_shop_unlinks(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url,390);seed_catalog(p);stub(p,PIZZA);upload(p);p.click('#scanRun')
    p.locator('.scan-row > button').click();p.click('#scanAddRow')
    row=p.locator('.scan-row');name=row.locator('[data-scan-field=name]')
    name.fill('пицца')
    expect(row.locator('.scan-catalog-option[role=option]')).to_have_count(2)
    name.press('ArrowUp')
    expect(row.locator('.scan-catalog-option[role=option]').last).to_have_attribute('aria-selected','true')
    name.fill('uhb,yjq') # грибной, wrong layout
    expect(row.locator('.scan-catalog-option[role=option]')).to_have_count(1)
    name.press('ArrowDown');name.press('Enter')
    expect(row.locator('.scan-match')).to_contain_text('Грибной')
    expect(row.locator('[data-scan-field=price]')).to_have_value('')
    row.locator('[data-scan-field=price]').fill('4.99')
    expect(row.locator('[data-scan-field=total]')).to_have_value('4.99')
    p.locator('#scanConfirmed').check();p.fill('#scanShop','Другой магазин')
    expect(p.locator('#scanConfirmed')).not_to_be_checked()
    expect(row.locator('.scan-match')).not_to_contain_text('Из каталога')
    name.fill('черри');name.press('ArrowDown');name.press('Enter')
    name.fill('Ручное название без каталога')
    name.press('Escape')
    expect(p.locator('#receiptScanDialog')).to_be_visible()
    expect(row.locator('.scan-catalog-list')).to_be_hidden()
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert payload[0]['name']=='Ручное название без каталога' and not payload[0].get('product_id')
    assert not payload[0].get('template_id')

@pytest.mark.e2e
def test_other_store_and_unknown_price_never_import_catalog_price(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url);seed_catalog(p);stub(p,PIZZA);upload(p);p.click('#scanRun')
    p.fill('#scanShop','Новый магазин')
    row=p.locator('.scan-row').first;row.locator('[data-scan-field=price]').fill('')
    row.locator('.scan-suggestion').first.click()
    expect(row.locator('[data-scan-field=price]')).to_have_value('')
    p.locator('#scanConfirmed').check();expect(p.locator('#scanTransfer')).to_be_disabled()
    row.locator('[data-scan-field=price]').fill('4.99');p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert payload[0]['product_id']==901 and not payload[0].get('template_id') and not payload[0].get('source_id')


def paste_image(p, buffer):
    return p.evaluate('''encoded=>{
      const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));const data=new DataTransfer();
      data.items.add(new File([bytes],'clipboard.png',{type:'image/png'}));
      const event=new ClipboardEvent('paste',{clipboardData:data,bubbles:true,cancelable:true});
      document.querySelector('#receiptScanDialog').dispatchEvent(event);return event.defaultPrevented;
    }''',base64.b64encode(buffer).decode())

@pytest.mark.e2e
def test_paste_image_review_replacement_and_text_passthrough(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url,390);stub(p,PIZZA)
    picture=image(p);assert paste_image(p,picture['buffer'])
    expect(p.locator('#scanRun')).to_be_enabled();p.click('#scanRun')
    expect(p.locator('.scan-row')).to_have_count(1)
    assert p.evaluate('''()=>{const data=new DataTransfer();data.setData('text/plain','Молоко');const event=new ClipboardEvent('paste',{clipboardData:data,bubbles:true,cancelable:true});document.querySelector('[data-scan-field=name]').dispatchEvent(event);return !event.defaultPrevented;}''')
    assert paste_image(p,picture['buffer']);expect(p.locator('#scanPasteReplace')).to_be_visible()
    p.click('#scanPasteDismiss');expect(p.locator('#scanReview')).to_be_visible()
    assert paste_image(p,picture['buffer']);p.click('#scanPasteAccept')
    expect(p.locator('#scanReview')).to_be_hidden();expect(p.locator('#scanRun')).to_be_enabled()
    p.click('#scanRun');expect(p.locator('.scan-row')).to_have_count(1)

@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_upload_crop_fit_content_and_keyword_empty_state(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);seed_catalog(p)
    dialog=p.locator('#receiptScanDialog')
    expect(p.locator('#scanDropzone')).to_be_visible()
    expect(p.locator('#scanDropzone')).to_contain_text('Ctrl+V')
    expect(p.locator('#scanRun')).to_be_hidden()
    box=dialog.bounding_box();assert box['width']<=520 and box['height']<450
    p.screenshot(path=f'/tmp/fa-scan-upload-compact-{width}.png')
    with p.expect_file_chooser() as chooser:
        p.locator('#scanDropzone').click()
    chooser.value.set_files(image(p))
    expect(dialog).to_have_attribute('data-stage','crop')
    expect(p.locator('#scanDropzone')).to_be_hidden()
    expect(p.locator('#scanRun')).to_be_enabled()
    assert dialog.bounding_box()['width']<700
    assert dialog.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    run=p.locator('#scanRun').bounding_box();bar=p.locator('#scanRunBar').bounding_box()
    assert abs(run['x']+run['width']-bar['x']-bar['width'])<2
    assert p.locator('#scanRun svg').count()==1
    p.screenshot(path=f'/tmp/fa-scan-crop-compact-{width}.png')
    stub(p,PIZZA.replace('ПИЦЦА КУСОК ЧЕРРИ ЧЕДЕР 200Г','Абрикосовый джем'))
    p.click('#scanRun')
    expect(p.locator('.scan-match')).to_contain_text('В каталоге нет совпадений по словам')
    expect(p.locator('[data-scan-field=name]')).to_have_value('Абрикосовый джем')
    expect(p.locator('[data-scan-field=price]')).to_have_value('4.99')
    p.screenshot(path=f'/tmp/fa-scan-no-match-{width}.png')
    # Background whitespace inside the dialog should not discard a review.
    dialog.click(position={'x':4,'y':4})
    expect(dialog).to_be_visible()

@pytest.mark.e2e
def test_drop_image_and_multiple_files_validation(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url)
    picture=image(p)
    encoded=base64.b64encode(picture['buffer']).decode()
    def drop(count):
        return p.evaluate('''({encoded,count})=>{
          const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));const data=new DataTransfer();
          for(let i=0;i<count;i++)data.items.add(new File([bytes],`receipt${i}.png`,{type:'image/png'}));
          const target=document.querySelector('#scanDropzone');
          target.dispatchEvent(new DragEvent('dragover',{dataTransfer:data,bubbles:true,cancelable:true}));
          target.dispatchEvent(new DragEvent('drop',{dataTransfer:data,bubbles:true,cancelable:true}));
        }''',{'encoded':encoded,'count':count})
    drop(2);expect(p.locator('#scanStatus')).to_contain_text('одно фото')
    expect(p.locator('#scanDropzone')).to_be_visible()
    drop(1);expect(p.locator('#receiptScanDialog')).to_have_attribute('data-stage','crop')
    expect(p.locator('#scanRun')).to_be_enabled()

@pytest.mark.e2e
def test_catalog_failure_is_not_reported_as_no_matches(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock
    p.route('**/api/v1/operations/catalog-products?**',lambda route:route.fulfill(status=503,json={'detail':'Unavailable'}))
    p.route('**/api/v1/operations/item-templates?**',lambda route:route.fulfill(status=503,json={'detail':'Unavailable'}))
    start(p,static_server_url);stub(p,PIZZA);upload(p);p.click('#scanRun')
    expect(p.locator('.scan-match')).to_contain_text('Каталог загружен не полностью')
    expect(p.locator('.scan-match')).not_to_contain_text('нет совпадений')
    expect(p.locator('[data-scan-field=price]')).to_have_value('4.99')

WEIGHTED='''ООО ГРИНРОЗНИЦА
№ ДОК 179487
Колбаса Рубленая варено-копченая в/с
2231860229407 18.69 x0.530 9.91
ИТОГО К ОПЛАТЕ 9.91
13.10.2026 15:07:01'''

@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_new_scan_weighted_unit_transfer_and_live_operation_labels(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);stub(p,WEIGHTED);upload(p);p.click('#scanRun')
    row=p.locator('.scan-row')
    expect(row.locator('[data-scan-unit=""]')).to_have_attribute('aria-pressed','true')
    row.locator('[data-scan-unit=kg]').click()
    expect(row.locator('[data-scan-field=price]').locator('..')).to_contain_text('Цена за кг')
    expect(row.locator('[data-scan-field=quantity]').locator('..')).to_contain_text('Вес, кг')
    expect(row.locator('[data-scan-field=total]')).to_have_value('9.91')
    p.screenshot(path=f'/tmp/fa-scan-unit-{width}.png',animations='disabled')
    assert p.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert payload[0]['sale_unit']=='kg' and payload[0]['package_unit'] is None
    assert float(payload[0]['quantity'])==.53 and float(payload[0]['unit_price'])==18.69
    row=p.locator('#receiptItemsList .receipt-item-row').first
    expect(row.locator('.receipt-known-price-label')).to_have_text('Цена за кг')
    expect(row.locator('.receipt-quantity-cell > span')).to_have_text('Вес, кг')
    # Change the unit without rebuilding the editor; labels must update immediately.
    row.locator('[data-receipt-field=sale_unit]').evaluate("n=>{n.value='g';n.dispatchEvent(new Event('input',{bubbles:true}));}")
    expect(row.locator('.receipt-known-price-label')).to_have_text('Цена за г')
    expect(row.locator('.receipt-quantity-cell > span')).to_have_text('Вес, г')

@pytest.mark.e2e
def test_scan_catalog_unit_default_manual_override_and_unlink(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url);seed_catalog(p)
    p.evaluate("Object.assign(window.App.state.receiptProductHints[0],{sale_unit:'piece',package_quantity:200,package_unit:'g'})")
    stub(p,PIZZA);upload(p);p.click('#scanRun');row=p.locator('.scan-row')
    row.locator('.scan-suggestion').first.click()
    expect(row.locator('[data-scan-unit=piece]')).to_have_attribute('aria-pressed','true')
    row.get_by_role('button',name='Отвязать товар каталога').click()
    expect(row.locator('[data-scan-unit=""]')).to_have_attribute('aria-pressed','true')
    row.locator('[data-scan-unit=kg]').click();row.locator('.scan-suggestion').first.click()
    expect(row.locator('[data-scan-unit=kg]')).to_have_attribute('aria-pressed','true')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert payload[0]['sale_unit']=='kg' and payload[0]['package_quantity'] is None


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_scan_category_search_manual_priority_and_transfer(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);seed_catalog(p);stub(p,PIZZA);upload(p);p.click('#scanRun')
    row=p.locator('.scan-row').first
    category=row.locator('[data-scan-category]')
    expect(category).to_have_value('')
    row.locator('.scan-suggestion').first.click()
    expect(category).to_have_value('101')
    category.click()
    picker=p.locator('#appChoiceDialog')
    expect(picker).to_be_visible()
    categories=p.evaluate("window.App.state.categories.filter(c=>c.kind==='expense'&&c.id!==101)")
    chosen=categories[0]
    picker.get_by_role('searchbox').fill(chosen['name'])
    picker.get_by_role('button',name=chosen['name'],exact=True).click()
    expect(category).to_have_value(str(chosen['id']))
    row.get_by_role('button',name='Отвязать товар каталога').click()
    expect(category).to_have_value(str(chosen['id']))
    row.locator('.scan-suggestion').first.click()
    expect(category).to_have_value(str(chosen['id']))
    # New, uncatalogued items retain the user's category after editing the name.
    row.locator('[data-scan-field=name]').fill('Новая пицца')
    row.locator('[data-scan-field=name]').press('Escape')
    expect(category).to_have_value(str(chosen['id']))
    p.screenshot(path=f'/tmp/fa-scan-category-{width}.png')
    assert p.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert item['category_id']==chosen['id'] and item['category_touched'] is True
    assert not item.get('product_id') and float(item['unit_price'])==4.99
