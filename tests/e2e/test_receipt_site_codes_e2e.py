import json
import base64
from io import BytesIO
from PIL import Image
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock
from tests.e2e.test_receipt_scan_e2e import start, stub, upload

TEXT='''ООО «Либретик»
4811040140757 Пельмени 430г
5.99 x1.000 5.99
ИТОГО К ОПЛАТЕ 5.99
19.10.2026 20:00:00'''


def setup(page, url, results):
    page.route('**/catalog-products/lookup-codes', lambda r: r.fulfill(json={'items': [], 'auto_match': False}))
    page.route('**/catalog-products/lookup-site-codes', lambda r: r.fulfill(json=results))
    start(page, url); stub(page, TEXT); upload(page); page.click('#scanRun')


@pytest.mark.e2e
def test_site_exact_match_keeps_receipt_amount_and_draft_selection(static_server_url, page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;calls=[]
    p.on('request', lambda r: calls.append(r.post_data_json) if r.url.endswith('/lookup-site-codes') else None)
    setup(p, static_server_url, {'items':[{'name':'Пельмени Бульварские 430 г','url':'https://sosedi-dostavka.by/products/pelmeni-42','site_selection':'signed-selection'}],'auto_match':True,'source':'Соседи'})
    expect(p.locator('#scanShop')).to_have_value('Соседи')
    expect(p.locator('.receipt-product-preview')).to_have_count(1)
    expect(p.locator('[data-scan-field=name]').first).to_have_value('ООО «Либретик» Пельмени 430г')
    p.get_by_role('button',name='Выбрать ссылку',exact=True).click()
    p.get_by_role('button',name='Использовать название',exact=True).click()
    expect(p.locator('[data-scan-field=name]').first).to_have_value('Пельмени Бульварские 430 г')
    expect(p.locator('[data-scan-field=price]').first).to_have_value('5.99')
    expect(p.locator('[data-scan-field=total]').first).to_have_value('5.99')
    assert calls and calls[0]['shop_name']=='Соседи'
    assert set(calls[0])=={'codes','shop_name'}
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert payload[0]['site_selection']=='signed-selection' and float(payload[0]['unit_price'])==5.99
    expect(p.locator('#opAmount')).to_have_value('5.99')
    attachment=p.evaluate("window.App.getRuntimeModule('receipt-scan').payload('create')")
    assert 'site_selection' not in attachment['review']['rows'][0]


@pytest.mark.e2e
def test_multiple_site_matches_require_choice_and_shop_change_drops_selection(static_server_url, page_with_receipt_api_mock):
    p=page_with_receipt_api_mock
    setup(p,static_server_url,{'items':[{'name':'Пельмени A 430 г','site_selection':'selection-a'},{'name':'Пельмени B 430 г','site_selection':'selection-b'}],'auto_match':False,'source':'Соседи'})
    # Reuse the existing code result buttons for explicit choices.
    p.wait_for_function("document.querySelector('.scan-codes-host')?.textContent.includes('Пельмени A')")
    card=p.locator('.receipt-product-preview').filter(has_text='Пельмени B 430 г')
    card.get_by_role('button',name='Выбрать ссылку').click()
    card.get_by_role('button',name='Использовать название').click()
    expect(p.locator('[data-scan-field=name]').first).to_have_value('Пельмени B 430 г')
    p.route('**/catalog-products/lookup-site-codes', lambda r:r.fulfill(json={'items':[],'state':'unsupported'}))
    p.fill('#scanShop','Маяк')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert not payload[0]['site_selection'] and float(payload[0]['unit_price'])==5.99


@pytest.mark.e2e
def test_partial_source_search_refreshes_when_load_finishes_and_enter_chooses_match(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock
    start(p,static_server_url);stub(p);upload(p);p.click('#scanRun')
    p.evaluate('''()=>{
      window.App.state.itemSources=[];
      window.App.getRuntimeModule('item-catalog').loadItemSources=()=>new Promise(resolve=>{
        window.finishSources=()=>{window.App.state.itemSources=[{id:301,name:'Соседи'}];resolve();};
      });
    }''')
    shop=p.locator('#scanShop');popup=p.locator('#scanReceiptStoreOptions')
    shop.fill('Сос')
    p.evaluate('window.finishSources()')
    expect(popup.get_by_role('option',name='Соседи',exact=True)).to_be_visible()
    shop.press('Enter');expect(shop).to_have_value('Соседи')
    for text in ['С','Со','Сосе','cjc','Либретик','Либретек']:
        shop.fill(text);expect(popup.get_by_role('option',name='Соседи',exact=True)).to_be_visible()
    shop.press('Enter');expect(shop).to_have_value('Соседи')


@pytest.mark.e2e
def test_old_store_response_is_ignored_after_manual_source_change(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;pending=[]
    p.route('**/catalog-products/lookup-codes',lambda r:r.fulfill(json={'items':[],'auto_match':False}))
    def site_route(route):
        if route.request.post_data_json['shop_name']=='Соседи': pending.append(route)
        else: route.fulfill(json={'items':[{'name':'Пельмени Green 430 г','site_selection':'green-selection'}],'auto_match':True})
    p.route('**/catalog-products/lookup-site-codes',site_route)
    start(p,static_server_url);stub(p,TEXT);upload(p);p.click('#scanRun')
    p.wait_for_event('request',predicate=lambda r:r.url.endswith('/lookup-site-codes'))
    p.fill('#scanShop','Green')
    expect(p.locator('.receipt-product-preview')).to_contain_text('Пельмени Green 430 г')
    p.get_by_role('button',name='Выбрать ссылку',exact=True).click()
    p.get_by_role('button',name='Использовать название',exact=True).click()
    expect(p.locator('[data-scan-field=name]').first).to_have_value('Пельмени Green 430 г')
    assert pending
    pending[0].fulfill(json={'items':[{'name':'Старый ответ Соседей','site_selection':'stale-selection'}],'auto_match':True})
    expect(p.locator('[data-scan-field=name]').first).to_have_value('Пельмени Green 430 г')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert payload[0]['site_selection']=='green-selection' and payload[0]['shop_name']=='Green'


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_preview_is_read_only_responsive_and_other_store_never_links(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock
    p.route('**/catalog-products/lookup-codes',lambda r:r.fulfill(json={'items':[],'auto_match':False}))
    def site(route):
        other=route.request.post_data_json.get('other_sources',False)
        route.fulfill(json={'state':'found','items':[{'name':'Пельмени Бульварские с очень длинным названием 430 г','size_label':'430 г','brand':'Бульварские','url':'https://green-dostavka.by/product/pelmeni-42/','source':'Green','matched_by':'barcode','matched_code':'04811040140757','reference_only':other,'site_selection':None if other else 'selection','image_token':'image'}]})
    p.route('**/catalog-products/lookup-site-codes',site)
    photo=BytesIO();Image.new('RGB',(80,80),'white').save(photo,'JPEG')
    photo_data='data:image/jpeg;base64,'+base64.b64encode(photo.getvalue()).decode()
    p.route('**/catalog-products/receipt-thumbnail',lambda r:r.fulfill(json={'image':photo_data if width==390 else None}))
    start(p,static_server_url,width);stub(p,TEXT);upload(p);p.click('#scanRun')
    card=p.locator('.receipt-product-preview')
    expect(card).to_contain_text('Штрихкод совпадает')
    expect(card).to_contain_text('Фасовка на сайте: 430 г')
    if width==390:
        expect(card.locator('img')).to_be_visible()
        expect(card.locator('img')).to_have_attribute('src',photo_data)
    expect(p.locator('[data-scan-field=name]').first).to_have_value('ООО «Либретик» Пельмени 430г')
    expect(p.locator('[data-scan-field=price]').first).to_have_value('5.99')
    expect(p.locator('[data-scan-field=total]').first).to_have_value('5.99')
    assert p.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    assert card.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    card.scroll_into_view_if_needed();p.screenshot(path=f'/tmp/fa-product-preview-{width}.png')
    p.get_by_role('button',name='Другие магазины',exact=True).click()
    expect(card).to_contain_text('Другой магазин · для сверки')
    expect(card.get_by_role('button',name='Выбрать ссылку')).to_have_count(0)
    expect(p.get_by_role('link',name='Поиск в интернете',exact=True)).to_have_attribute('href','https://www.google.com/search?q=%224811040140757%22')
    web=p.get_by_role('link',name='Поиск в интернете',exact=True)
    web.scroll_into_view_if_needed()
    assert web.evaluate('''n=>{const range=document.createRange();range.selectNodeContents(n);
      const text=range.getBoundingClientRect(),box=n.getBoundingClientRect();
      return Math.abs(text.y+text.height/2-box.y-box.height/2)<2
        && Math.abs(text.x+text.width/2-box.x-box.width/2)<2;}''')
    p.screenshot(path=f'/tmp/fa-preview-button-fix-{width}.png')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    data=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert not data[0]['site_selection'] and float(data[0]['unit_price'])==5.99


@pytest.mark.e2e
def test_article_only_preview_stays_inside_selected_store(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;requests=[]
    p.route('**/catalog-products/lookup-codes',lambda r:r.fulfill(json={'items':[],'auto_match':False}))
    def site(r):
        requests.append(r.request.post_data_json)
        r.fulfill(json={'state':'found','items':[{'name':'Пицца Микс 170 г','url':'https://edostavka.by/product/2229644','source':'Е-доставка','matched_by':'retailer','matched_code':'2229644','site_selection':'article-selection'}]})
    p.route('**/catalog-products/lookup-site-codes',site)
    start(p,static_server_url,390);stub(p,'ООО Евроторг\n№ ДОК 123\n2229644 Пицца Микс 170г\n3.99 x1.000 3.99\nИТОГО К ОПЛАТЕ 3.99\n23.10.2026 12:00:00');upload(p);p.click('#scanRun')
    expect(p.locator('.receipt-product-preview')).to_contain_text('Артикул совпадает · 2229644')
    assert requests[0]['shop_name']=='Евроопт' and requests[0]['codes']==[{'kind':'retailer','code':'2229644'}]
    expect(p.get_by_role('button',name='Другие магазины',exact=True)).to_have_count(0)
    expect(p.get_by_role('link',name='Поиск в интернете',exact=True)).to_have_count(0)
    expect(p.locator('[data-scan-field=price]').first).to_have_value('3.99')
    p.get_by_role('button',name='Выбрать ссылку',exact=True).click()
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    data=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert data[0]['site_selection']=='article-selection' and float(data[0]['unit_price'])==3.99
