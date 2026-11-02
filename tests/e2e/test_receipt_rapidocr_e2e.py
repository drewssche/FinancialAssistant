import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_scan_e2e import start, upload, TEXT, stub
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_explicit_remote_choice_privacy_preview_and_manual_confirmation(static_server_url,page_with_receipt_api_mock,width):
    page=page_with_receipt_api_mock;sent=[]
    page.route('**/api/v1/receipt-ocr/status',lambda r:r.fulfill(json={'available':True}))
    def recognize(route):
        sent.append(route.request.headers.get('content-type'))
        route.fulfill(json={'text':TEXT,'blocks':[],'engine':'rapidocr-v5-eslav'})
    page.route('**/api/v1/receipt-ocr/recognize',recognize)
    start(page,static_server_url,width)
    expect(page.locator('#scanEngine')).to_have_value('local')
    upload(page);assert sent==[]
    page.locator('#scanEngine').select_option('rapid')
    expect(page.locator('#scanPrivacy')).to_contain_text('сервер ФинАсиста')
    assert sent==[]
    page.click('#scanRun');expect(page.locator('#scanReview')).to_be_visible()
    assert sent==['image/jpeg']
    expect(page.locator('#scanTotal')).to_have_value('7.50')
    expect(page.locator('#scanTransfer')).to_be_disabled()
    assert page.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    page.screenshot(path=f'/tmp/fa-rapidocr-review-{width}.png')
    page.locator('#scanConfirmed').check();page.click('#scanTransfer')
    expect(page.locator('#opAmount')).to_have_value('7.50')


@pytest.mark.e2e
def test_remote_busy_can_retry_locally_without_auto_switch(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock
    page.route('**/api/v1/receipt-ocr/status',lambda r:r.fulfill(json={'available':True}))
    page.route('**/api/v1/receipt-ocr/recognize',lambda r:r.fulfill(status=429,json={'detail':'Распознавание занято'}))
    start(page,static_server_url,390);upload(page);page.locator('#scanEngine').select_option('rapid');page.click('#scanRun')
    expect(page.locator('#scanStatus')).to_contain_text('занято')
    expect(page.locator('#scanEngine')).to_have_value('rapid')
    expect(page.locator('#scanReview')).not_to_be_visible()
    page.locator('#scanEngine').select_option('local');stub(page);page.click('#scanRun')
    expect(page.locator('#scanReview')).to_be_visible()


@pytest.mark.e2e
def test_cancel_remote_ignores_late_result(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock
    page.route('**/api/v1/receipt-ocr/status',lambda r:r.fulfill(json={'available':True}))
    start(page,static_server_url);upload(page);page.locator('#scanEngine').select_option('rapid')
    page.evaluate("window.App.receiptScanEngine.recognizeRemote=()=>({cancel(){window.remoteCancelled=true},promise:new Promise(r=>window.finishRemote=r)})")
    page.click('#scanRun');page.click('#scanCancel')
    page.evaluate('text=>window.finishRemote({text})',TEXT)
    expect(page.locator('#scanReview')).not_to_be_visible()
    assert page.evaluate('window.remoteCancelled')
    expect(page.locator('#scanRun')).to_be_enabled()


@pytest.mark.e2e
def test_remote_preparation_respects_crop_and_preserves_colour(page):
    from pathlib import Path
    page.evaluate('window.App={}')
    page.add_script_tag(path=str(Path('static/js/app-receipt-scan-image.js').resolve()))
    result=page.evaluate('''()=>{
      const c=document.createElement('canvas');c.width=400;c.height=200;
      const x=c.getContext('2d');x.fillStyle='#e02040';x.fillRect(0,0,200,200);x.fillStyle='#2080e0';x.fillRect(200,0,200,200);
      const crop=[[0,0],[.5,0],[.5,1],[0,1]];
      const remote=App.receiptScanImage.prepare(c,crop,{enhance:false});
      const local=App.receiptScanImage.prepare(c,crop);
      const pixel=a=>Array.from(a.getContext('2d').getImageData(100,100,1,1).data);
      return {remote:pixel(remote),local:pixel(local),width:remote.width,height:remote.height,source:pixel(c)};
    }''')
    assert result['remote']==result['source']==[224,32,64,255]
    assert result['width']==result['height']==1000
    assert result['local'][0]==result['local'][1]==result['local'][2]
