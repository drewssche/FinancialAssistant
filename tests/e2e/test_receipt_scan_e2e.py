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
