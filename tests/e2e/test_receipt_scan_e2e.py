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
4810000000001 3.00 x2.000 6.00
Скидка -0.50
Хлеб
4810000000002 2.00 x1.000 2.00
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
    page.on('request',lambda r:writes.append(r.url) if r.method in ['POST','PUT','PATCH','DELETE'] and '/api/v1/operations' in r.url else None)
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
    assert payload[0]['note'].startswith('OCR: ')
    assert payload[0].get('template_id') is None and payload[0].get('variant_id') is None
    expect(page.locator('#opAmount')).to_have_value('7.50')
    expect(page.locator('#opDate')).to_have_value('2026-10-12')
    # Transfer is a draft-only action, and another scan cannot overwrite it.
    page.click('#openReceiptScan');stub(page);upload(page);page.click('#scanRun');page.locator('#scanConfirmed').check();page.click('#scanTransfer')
    expect(page.locator('#scanStatus')).to_contain_text('уже есть данные')
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
