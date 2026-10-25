import ast
import base64
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login, _ensure_categories_loaded

TEXT='''ООО Тестовый магазин
№ ДОК 123
Молоко 1 л
4006381333931 3.00 x2.000 6.00
Скидка -0.50
Хлеб
4811040140757 2.00 x1.000 2.00
ИТОГО К ОПЛАТЕ 7.50
12.10.2026 18:24:04'''

def start(page,url,width=1440):
    page.set_viewport_size({'width':width,'height':1000})
    page.goto(url+'/static/index.html');_login(page);_ensure_categories_loaded(page)
    page.click('#addOperationCta');page.click('#createOperationModeSwitch [data-operation-mode=receipt]');page.click('#openReceiptScan')
    expect(page.locator('#receiptScanDialog')).to_be_visible()

def image(page):
    value=page.evaluate('''() => {const c=document.createElement('canvas');c.width=1200;c.height=1600;const x=c.getContext('2d');x.fillStyle='white';x.fillRect(0,0,1200,1600);x.fillStyle='black';x.font='36px Arial';const lines=['ООО ТЕСТОВЫЙ МАГАЗИН','№ ДОК 123','МОЛОКО','3.00 x2.000 6.00','ХЛЕБ','2.00 x1.000 2.00','ИТОГО К ОПЛАТЕ 8.00','12.10.2026 18:24:04'];lines.forEach((s,i)=>x.fillText(s,80,120+i*90));return c.toDataURL('image/png').split(',')[1];}''')
    return {'name':'receipt.png','mimeType':'image/png','buffer':base64.b64decode(value)}

def upload(page):
    page.locator('#scanFile').set_input_files(image(page))
    expect(page.locator('#scanRun')).to_be_enabled()

def stub(page,text=TEXT):
    page.evaluate('''text=>{window.App.receiptScanEngine.recognize=()=>({cancel(){},promise:Promise.resolve({text,blocks:[]})});}''',text)

@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1024,1100,1440])
def test_scan_review_to_unsaved_operation(static_server_url,page_with_receipt_api_mock,width):
    page=page_with_receipt_api_mock;errors=[];writes=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:writes.append(r.url) if r.method in ['POST','PUT','PATCH','DELETE'] and '/api/v1/operations' in r.url and not r.url.endswith('/lookup-codes') else None)
    start(page,static_server_url,width);stub(page);upload(page)
    page.screenshot(path=f'/tmp/fa-ocr-crop-{width}.png')
    page.click('#scanRun');expect(page.locator('#scanReview')).to_be_visible()
    expect(page.locator('#scanRows .scan-row')).to_have_count(2)
    expect(page.locator('#scanTransfer')).to_be_disabled()
    expect(page.locator('#scanDate')).to_have_value('2026-10-12')
    page.screenshot(path=f'/tmp/fa-ocr-review-{width}.png')
    assert page.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    page.locator('#scanConfirmed').check();expect(page.locator('#scanTransfer')).to_be_enabled()
    page.click('#scanTransfer');expect(page.locator('#receiptScanDialog')).not_to_be_visible()
    payload=page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert len(payload)==2 and payload[0]['name']=='Молоко 1 л'
    assert payload[0]['quantity']=='2' and payload[0]['discount_mode']=='amount'
    assert float(payload[0]['discount_value'])==.5 and payload[0]['package_unit'] is None
    assert not payload[0].get('note')
    assert payload[0].get('template_id') is None and payload[0].get('variant_id') is None
    expect(page.locator('#opAmount')).to_have_value('7.50')
    expect(page.locator('#opDate')).to_have_value('2026-10-12')
    # Review survives closing and follows edits made in the operation.
    page.click('#openReceiptScan')
    expect(page.locator('#scanReview')).to_be_visible()
    expect(page.locator('#scanTotal')).to_have_value('7.50')
    page.locator('#scanConfirmed').check();page.click('#scanTransfer')
    expect(page.locator('#scanReplaceOperation')).to_be_visible()
    page.click('#scanReplaceNo');page.click('#scanClose')
    assert page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()") == payload
    assert writes==[] and errors==[]

@pytest.mark.e2e
def test_scan_arithmetic_correction_text_and_cancel(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock;start(page,static_server_url,390);stub(page,TEXT.replace('7.50','7.00'));upload(page);page.click('#scanRun')
    page.locator('#scanConfirmed').check();expect(page.locator('#scanTransfer')).to_be_disabled()
    page.fill('#scanTotal','7.50');expect(page.locator('#scanConfirmed')).not_to_be_checked()
    page.click('#scanShowText');expect(page.locator('#scanTextDialog')).to_be_visible()
    page.locator('#scanText').press('Escape');expect(page.locator('#scanTextDialog')).not_to_be_visible()
    expect(page.locator('#receiptScanDialog')).to_be_visible()
    page.click('#scanClose');expect(page.locator('#createModal')).to_be_visible()
    assert not page.evaluate("window.App.state.createReceiptItems.some(x=>x.name)")

@pytest.mark.e2e
def test_scan_late_result_and_failure_retry(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock;start(page,static_server_url);upload(page)
    page.evaluate("window.App.receiptScanEngine.recognize=()=>({cancel(){window.cancelled=true;},promise:new Promise(r=>window.lateScan=r)});")
    page.click('#scanRun');expect(page.locator('#scanCancel')).to_be_visible();page.click('#scanCancel')
    page.evaluate('text=>window.lateScan({text})',TEXT)
    expect(page.locator('#scanReview')).not_to_be_visible()
    assert page.evaluate('window.cancelled')
    page.evaluate("window.App.receiptScanEngine.recognize=()=>({cancel(){},promise:Promise.reject(new Error('Тестовая ошибка'))});")
    page.click('#scanRun');expect(page.locator('#scanStatus')).to_contain_text('Тестовая ошибка')
    expect(page.locator('#scanRun')).to_be_enabled();stub(page);page.click('#scanRun');expect(page.locator('#scanReview')).to_be_visible()

@pytest.mark.e2e
def test_real_local_ocr_engine(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock;external=[];errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:external.append(r.url) if any(s in r.url for s in ['jsdelivr','projectnaptha','unpkg']) else None)
    # Exercise the production CSP, including the isolated same-origin OCR document.
    csp=next(n.value for n in ast.walk(ast.parse(Path('app/main.py').read_text())) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith("default-src 'self';"))
    def policy(route):
        response=route.fetch();route.fulfill(response=response,headers={**response.headers,'Content-Security-Policy':csp})
    page.route('**/static/*.html*',policy)
    start(page,static_server_url);upload(page)
    page.click('#scanRun');expect(page.locator('#scanReview')).to_be_visible(timeout=90000)
    expect(page.locator('#scanText')).to_have_value(__import__('re').compile('ИТОГО'))
    expect(page.locator('#scanRows .scan-row')).to_have_count(2)
    expect(page.locator('#scanDate')).to_have_value('2026-10-12')
    Path('/tmp/fa-ocr-real-result.json').write_text(json.dumps({'text':page.locator('#scanText').input_value(),'status':page.locator('#scanStatus').inner_text()},ensure_ascii=False))
    page.screenshot(path='/tmp/fa-ocr-real.png')
    assert external==[] and errors==[]


@pytest.mark.e2e
def test_engine_cancel_initialization_releases_frame(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock;start(page,static_server_url);upload(page)
    result=page.evaluate("""async()=>{
      let task;task=window.App.receiptScanEngine.recognize(document.querySelector('#scanCanvas'),()=>task.cancel());
      try{await task.promise;return 'unexpected success';}catch(e){return e.message;}
    }""")
    assert result=='Распознавание отменено'
    expect(page.locator('iframe[title="Локальное распознавание"]')).to_have_count(0)

@pytest.mark.e2e
def test_crop_geometry_and_invalid_file(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock;start(page,static_server_url,320)
    page.locator('#scanFile').set_input_files({'name':'x.svg','mimeType':'image/svg+xml','buffer':b'<svg></svg>'})
    expect(page.locator('#scanStatus')).to_contain_text('Выберите JPG')
    upload(page)
    page.locator('[data-corner="0"]').press('ArrowRight')
    assert '0.5%' in page.locator('[data-corner="0"]').get_attribute('style')
    page.click('#scanRotate')
    assert page.locator('#scanCanvas').evaluate('c=>c.width>c.height')
    result=page.evaluate("""()=>{try{window.App.receiptScanImage.prepare(document.querySelector('#scanCanvas'),[[0,0],[1,1],[1,0],[0,1]]);return false;}catch{return true;}}""")
    assert result

@pytest.mark.e2e
def test_unreadable_row_keeps_its_discount_and_requires_correction(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock;start(page,static_server_url,390)
    stub(page,'ООО Тест\n№ ДОК\nМолоко\n3.00 x1.000 3.00\nХлеб\n1.99 х!.000 1.99\nСкидка -0.60\nИТОГО К ОПЛАТЕ 4.39\n14.10.2026 10:20:30')
    upload(page);page.click('#scanRun')
    rows=page.locator('#scanRows .scan-row');expect(rows).to_have_count(2)
    expect(rows.nth(0).locator('[data-scan-field=discount]')).to_have_value('0.00')
    expect(rows.nth(1).locator('[data-scan-field=price]')).to_have_value('')
    expect(rows.nth(1).locator('[data-scan-field=price]')).to_have_attribute('placeholder','Не распознано')
    expect(rows.nth(1).locator('[data-scan-field=discount]')).to_have_value('0.60')
    page.locator('#scanConfirmed').check();expect(page.locator('#scanTransfer')).to_be_disabled()
    rows.nth(1).locator('[data-scan-field=price]').fill('1.99')
    rows.nth(1).locator('[data-scan-field=quantity]').fill('1')
    expect(page.locator('#scanConfirmed')).not_to_be_checked()
    page.locator('#scanConfirmed').check();expect(page.locator('#scanTransfer')).to_be_enabled()
    page.click('#scanTransfer')
    payload=page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert len(payload)==2 and not payload[0]['is_discounted']
    assert float(payload[1]['discount_value'])==.60
    expect(page.locator('#opAmount')).to_have_value('4.39')


@pytest.mark.e2e
def test_real_engine_repeated_rows_across_strip_boundaries(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock;start(page,static_server_url)
    value=page.evaluate('''() => {
      const c=document.createElement('canvas');c.width=1000;c.height=2600;
      const x=c.getContext('2d');x.fillStyle='white';x.fillRect(0,0,c.width,c.height);x.fillStyle='black';x.font='32px Arial';
      x.fillText('ООО ТЕСТОВЫЙ МАГАЗИН',60,70);x.fillText('№ ДОК 123',60,120);
      for(let i=0;i<14;i++){x.fillText('СЫРОК',60,200+i*140);x.fillText('1.10 x1.000 1.10',60,250+i*140);}
      x.fillText('ИТОГО К ОПЛАТЕ 15.40',60,2240);x.fillText('15.10.2026 21:23:00',60,2300);
      return c.toDataURL('image/png').split(',')[1];
    }''')
    page.locator('#scanFile').set_input_files({'name':'repeats.png','mimeType':'image/png','buffer':base64.b64decode(value)})
    expect(page.locator('#scanRun')).to_be_enabled();page.click('#scanRun')
    expect(page.locator('#scanReview')).to_be_visible(timeout=90000)
    expect(page.locator('#scanRows .scan-row')).to_have_count(14)
    expect(page.locator('#scanTotal')).to_have_value('15.40')
    expect(page.locator('#scanArithmetic')).to_contain_text('Суммы сходятся')
    names=page.locator('#scanRows [data-scan-field=name]').evaluate_all("ns=>ns.map(n=>n.value)")
    # OCR may spell Cyrillic as Latin lookalikes; this checks seam ownership,
    # not lexical accuracy (measured separately on actual photos).
    assert all(len(name.split())==1 and 4<=len(name)<=12 for name in names), names


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_scan_numeric_expressions_and_invalid_results(static_server_url,page_with_receipt_api_mock,width):
    page=page_with_receipt_api_mock;start(page,static_server_url,width)
    stub(page,'''ООО Green
№ ДОК 123
Пельмени
7.11 x1.000 7.11
Скидка -0.71
ИТОГО К ОПЛАТЕ 6.40
13.10.2026 18:24:04''');upload(page);page.click('#scanRun')
    row=page.locator('.scan-row').first
    paid=row.locator('[data-scan-field=total]')
    paid.fill('7,11−0,71');paid.press('Enter')
    expect(paid).to_have_value('6.40')
    expect(page.locator('#receiptScanDialog')).to_be_visible()
    expect(page.locator('#scanArithmetic')).to_contain_text('Суммы сходятся')
    for value in ['7,11-', '1/0', '-1', 'alert(1)', '10000000']:
        paid.fill(value);paid.press('Enter')
        expect(paid).to_have_value(value)
        expect(paid).to_have_attribute('aria-invalid','true')
        page.locator('#scanConfirmed').check()
        expect(page.locator('#scanTransfer')).to_be_disabled()
    paid.fill('(7,11 - 0,71) × 2 ÷ 2');paid.press('Tab')
    expect(paid).to_have_value('6.40')
    price=row.locator('[data-scan-field=price]');price.fill('14,22/2');price.press('Enter')
    expect(price).to_have_value('7.11')
    quantity=row.locator('[data-scan-field=quantity]');quantity.fill('(0,25+0,25)*2');quantity.press('Enter')
    expect(quantity).to_have_value('1')
    discount=row.locator('[data-scan-field=discount]');discount.fill('0,7+0,01');discount.press('Enter')
    expect(discount).to_have_value('0.71')
    page.locator('#scanTotal').fill('7,11-0,71');page.locator('#scanTotal').press('Tab')
    expect(page.locator('#scanTotal')).to_have_value('6.40')
    page.locator('#scanConfirmed').check();expect(page.locator('#scanTransfer')).to_be_enabled()
    page.screenshot(path=f'/tmp/fa-scan-math-{width}.png')
    page.click('#scanTransfer')
    payload=page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert float(payload['regular_unit_price'])==7.11 and float(payload['discount_value'])==.71
    assert float(payload['quantity'])==1 and float(page.locator('#opAmount').input_value())==6.40


@pytest.mark.e2e
def test_scan_missing_paid_total_and_manual_paid_recalculate_discount(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock;start(page,static_server_url)
    # Exercise a partially recognized row without fabricating a printed total.
    page.evaluate("""()=>{window.App.receiptScanParser.parse=()=>({
      date:'2026-10-13',shop:'Green',total:640,rows:[
        {name:'Пельмени',price:711,quantity:1,discount:71,total:null,source:'Частично распознано'}
      ]});}""")
    stub(page);upload(page);page.click('#scanRun')
    row=page.locator('.scan-row').first;paid=row.locator('[data-scan-field=total]')
    expect(paid).to_have_value('6.40')
    paid.focus();paid.press('Tab')
    row.locator('[data-scan-field=discount]').fill('0,70')
    expect(paid).to_have_value('6.41')
    # Entering paid adjusts the discount; later edits retain that discount amount.
    paid.fill('6,40');row.locator('[data-scan-field=price]').fill('7,12')
    expect(paid).to_have_value('6.41')
    expect(row.locator('[data-scan-field=discount]')).to_have_value('0.71')
    expect(page.locator('#scanArithmetic')).to_contain_text('не совпадает с итогом чека')
    expect(page.locator('#scanTransfer')).to_be_disabled()


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_scanned_amount_recalculates_on_edits_and_preserves_receipt_header(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width)
    stub(p,"ООО Соседи\n№ ДОК 1\nКуриное филе\n14.59 x0.320 2.29\nИТОГО К ОПЛАТЕ 2.29\n16.10.2026 20:34:51")
    upload(p);p.click('#scanRun');row=p.locator('.scan-row')
    price=row.locator('[data-scan-field=price]');qty=row.locator('[data-scan-field=quantity]')
    discount=row.locator('[data-scan-field=discount]');paid=row.locator('[data-scan-field=total]')
    expect(paid).to_have_value('2.29')  # Do not silently repair OCR on load.
    row.locator('[data-scan-unit=kg]').click();expect(paid).to_have_value('2.29')
    qty.fill('0,32');expect(paid).to_have_value('4.67')
    qty.fill('0,324');expect(paid).to_have_value('4.73')
    discount.fill('0,73');expect(paid).to_have_value('4.00')
    paid.fill('4-0,01');paid.press('Enter');expect(discount).to_have_value('0.74')
    expect(paid).to_have_value('3.99')
    qty.fill('0,32');expect(paid).to_have_value('3.93')
    price.fill('15');expect(paid).to_have_value('4.06')
    paid.fill('4,80');expect(discount).to_have_value('0.00')
    expect(row.locator('.scan-discount-type')).to_be_hidden()
    paid.fill('5');expect(discount).to_have_value('0.00')
    expect(row.locator('.scan-row-error')).to_contain_text('Проверьте цену, количество и скидку')
    p.locator('#scanConfirmed').check();expect(p.locator('#scanTransfer')).to_be_disabled()
    paid.fill('4,80');qty.fill('');expect(paid).to_have_value('')
    expect(p.locator('#scanTransfer')).to_be_disabled()
    qty.fill('0,32');expect(paid).to_have_value('4.80')
    discount.fill('0,13');expect(paid).to_have_value('4.67')
    expect(p.locator('#scanTotal')).to_have_value('2.29')
    p.locator('#scanTotal').fill('4.67');p.locator('#scanConfirmed').check()
    row.screenshot(path=f'/tmp/fa-scan-calculation-{width}.png')
    p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert float(item['quantity'])==.32 and float(item['regular_unit_price'])==15
    assert float(item['discount_value'])==.13 and item['sale_unit']=='kg'
    expect(p.locator('#opAmount')).to_have_value('4.67')


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_scan_errors_stay_with_their_rows_and_reindex_after_delete(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;start(p,static_server_url,width)
    lines=['ООО Соседи','№ ДОК 123']
    for n in range(1,10):
        lines.extend([f'Йогурт номер {n}',f'3.00 x1.000 {4 if n in (2,9) else 3}.00'])
    lines.extend(['ИТОГО К ОПЛАТЕ 29.00','25.10.2026 12:00:00'])
    stub(p,'\n'.join(lines));upload(p);p.click('#scanRun')
    rows=p.locator('#scanRows .scan-row')
    expect(rows).to_have_count(9)
    expect(p.locator('.scan-row-error:visible')).to_have_count(2)
    expect(rows.nth(1).locator('.scan-row-error')).to_contain_text('позиции 2')
    expect(rows.nth(8).locator('.scan-row-error')).to_contain_text('позиции 9')
    expect(p.locator('#scanArithmetic')).to_be_hidden()
    expect(p.locator('#scanTransfer')).to_be_disabled()
    rows.nth(1).locator('.scan-row-error').scroll_into_view_if_needed()
    p.screenshot(path=f'/tmp/fa-scan-row-errors-{width}.png')
    assert p.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    rows.nth(1).locator('[data-scan-field=price]').fill('4')
    expect(rows.nth(1).locator('.scan-row-error')).to_be_hidden()
    expect(p.locator('.scan-row-error:visible')).to_have_count(1)
    p.get_by_role('button',name='Удалить позицию 1',exact=True).click()
    expect(rows).to_have_count(8)
    expect(rows.nth(7).locator('.scan-row-error')).to_contain_text('позиции 8')
    expect(p.locator('#scanArithmetic')).to_contain_text('не совпадает с итогом чека')
    expect(p.locator('#scanArithmetic')).not_to_contain_text('Проверьте цену')
    rows.nth(7).locator('[data-scan-field=price]').fill('4')
    p.fill('#scanTotal','26.00')
    expect(p.locator('.scan-row-error:visible')).to_have_count(0)
    expect(p.locator('#scanArithmetic')).to_contain_text('Суммы сходятся')
    p.locator('#scanConfirmed').check()
    expect(p.locator('#scanTransfer')).to_be_enabled()
