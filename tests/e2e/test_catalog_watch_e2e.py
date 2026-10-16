import re
from urllib.parse import urlparse
import pytest
from playwright.sync_api import expect
from tests.e2e.test_product_primary_codes_e2e import setup, card
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_watch_link_preview_confirm_toggle_dashboard(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock
    s={'name':'Молоко 900 мл','price':'2.79','regular_price':'3.49','unit':'шт','available':True,'normalized':'Цена за 1 л. 3,10 р.','conditions':'Публичная цена сайта; адрес доставки не выбран.','url':'https://edostavka.by/product/18516','comparison_key':'test'}
    data={'enabled':False,'telegram_connected':True,'supported_offer_ids':[501],'offers':[]};writes=[]
    def route(r,req):
        path=urlparse(req.url).path
        if path.endswith('/catalog-watches'):
            return r.fulfill(json={'tracked_count':int(data['enabled']),'offers':[dict(o,product_id=401,product_name='Молоко') for o in data['offers']] if data['enabled'] else [],'events':[],'unlinked':[]})
        if path.endswith('/preview'):return r.fulfill(json=s)
        if req.method=='PUT':
            writes.append(req.post_data_json)
            if '/offers/' in path:data['offers']=[{'template_id':501,'snapshot':s,'checked_at':'2026-10-16T10:00:00Z','error':None}]
            else:data['enabled']=req.post_data_json['enabled']
        if req.method=='DELETE':data['offers']=[]
        return r.fulfill(json=data)
    p.route(re.compile(r'.*/api/v1/catalog-watches(?:/.*)?$'),route)
    setup(p,static_server_url,width)
    toggle=p.locator('#catalogProductWatch input');expect(toggle).not_to_be_checked();toggle.check();expect(toggle).to_be_checked()
    p.locator('[data-product-tab=offers]').click()
    host=p.locator('[data-offer-watch="501"]')
    host.locator('summary').click();host.locator('[data-watch-url]').fill(s['url']);host.locator('[data-watch-preview]').click()
    expect(host.get_by_text('Молоко 900 мл',exact=True)).to_be_visible()
    assert len(writes)==1
    host.locator('[data-watch-confirm]').click();expect(host.locator('[data-watch-remove]')).to_be_visible()
    assert writes[-1]['expected_key']=='test'
    host.scroll_into_view_if_needed()
    box=host.bounding_box();assert box['x']>=0 and box['x']+box['width']<=width+1
    p.screenshot(path=f'/tmp/fa-watch-{width}.png')
    toggle.uncheck();expect(toggle).not_to_be_checked()
    host.locator('[data-watch-remove]').click();expect(host.locator('[data-watch-search]')).to_be_visible()
    assert data['offers']==[]
    p.locator('#closeCatalogProductModalBtn').click()
    expect(p.locator('#dashboardProductWatches')).to_contain_text('Нет отслеживаемых товаров')


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,1440])
def test_search_current_source_codes_preview_then_confirm(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock
    hit={'url':'https://edostavka.by/product/2186323','name':'Пельмени Бульварские 430 г','price':'6.71','unit':'шт','available':True,'matched_query':'2186323','match_kind':'retailer'}
    snapshot={**hit,'regular_price':'6.71','normalized':'15,60 BYN/кг','conditions':'Цена сайта без адреса доставки','comparison_key':'size-430g'}
    data={'enabled':False,'telegram_connected':True,'supported_offer_ids':[501],'offers':[]};searches=[];writes=[]
    def route(r,req):
        path=urlparse(req.url).path
        if path.endswith('/search'):
            searches.append(req.post_data_json)
            return r.fulfill(json={'items':[hit]})
        if path.endswith('/preview'):return r.fulfill(json=snapshot)
        if req.method=='PUT':
            writes.append(req.post_data_json);data['offers']=[{'template_id':501,'snapshot':snapshot}]
        if path.endswith('/catalog-watches'):return r.fulfill(json={'tracked_count':0,'offers':[],'events':[],'unlinked':[]})
        return r.fulfill(json=data)
    p.route(re.compile(r'.*/api/v1/catalog-watches(?:/.*)?$'),route)
    setup(p,static_server_url,width)
    expect(p.locator('#catalogProductSizeNote')).to_have_count(0)
    expect(p.locator('.measurement-example')).to_have_count(0)
    p.locator('[data-product-tab=offers]').click()
    host=p.locator('[data-offer-watch="501"]');source=card(p)
    source.locator('[data-code=barcode]').fill('4811040140757')
    source.locator('[data-code=sku]').fill('2186323')
    host.locator('[data-watch-search]').click()
    expect(host.locator('[data-watch-select]')).to_be_visible()
    assert searches==[{'codes':[{'kind':'barcode','code':'4811040140757'},{'kind':'retailer','code':'2186323'}]}]
    assert writes==[]
    host.scroll_into_view_if_needed();p.screenshot(path=f'/tmp/fa-store-search-{width}.png')
    assert host.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    host.locator('[data-watch-select]').click();expect(host.locator('[data-watch-confirm]')).to_be_visible()
    assert writes==[]
    host.locator('[data-watch-confirm]').click();expect(host.locator('[data-watch-remove]')).to_be_visible()
    assert writes==[{'url':hit['url'],'expected_key':'size-430g','expected_name':hit['name']}]
    # Searching/linking does not erase edits to codes awaiting the product Save action.
    expect(source.locator('[data-code=sku]')).to_have_value('2186323')


@pytest.mark.e2e
def test_search_empty_failure_name_fallback_and_stale_response(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;searches=[];pending=[];mode=['empty']
    def route(r,req):
        path=urlparse(req.url).path
        if path.endswith('/search'):
            searches.append(req.post_data_json)
            if mode[0]=='pending':pending.append(r);return
            if mode[0]=='error':return r.fulfill(status=400,json={'detail':'Поиск временно недоступен'})
            return r.fulfill(json={'items':[]})
        if path.endswith('/catalog-watches'):return r.fulfill(json={'tracked_count':0,'offers':[],'events':[],'unlinked':[]})
        return r.fulfill(json={'enabled':False,'telegram_connected':False,'supported_offer_ids':[501],'offers':[]})
    p.route(re.compile(r'.*/api/v1/catalog-watches(?:/.*)?$'),route)
    setup(p,static_server_url,390);p.locator('[data-product-tab=offers]').click()
    host=p.locator('[data-offer-watch="501"]');button=host.locator('[data-watch-search]')
    button.click();expect(host.locator('[data-watch-result]')).to_contain_text('По кодам ничего не найдено')
    mode[0]='error';button.click();expect(host.locator('[data-watch-result]')).to_contain_text('Не удалось выполнить поиск')
    expect(button).to_be_enabled()
    mode[0]='empty';host.locator('summary').click();host.locator('[data-watch-name]').fill('Пельмени')
    host.locator('[data-watch-name-search]').click();expect(host.locator('[data-watch-result]')).to_contain_text('По названию ничего не найдено')
    assert searches[-1]=={'name':'Пельмени'}
    mode[0]='pending'
    with p.expect_request(lambda r:r.url.endswith('/search')):button.click()
    p.locator('#closeCatalogProductModalBtn').click()
    p.evaluate("window.App.getRuntimeModule('catalog-products').openEditor(401)")
    p.locator('[data-product-tab=offers]').click()
    pending[0].fulfill(json={'items':[{'name':'Устаревший результат','url':'https://edostavka.by/product/1'}]})
    expect(host).not_to_contain_text('Устаревший результат')


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_green_sosedi_saved_links_and_source_labels(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;writes=[]
    meta={'501':{'provider':'green','source':'Green','search':False,'example_url':'https://green-dostavka.by/product/…','saved_url':'https://green-dostavka.by/product/moloko-123/'},'502':{'provider':'sosedi','source':'Соседи','search':False,'example_url':'https://sosedi-dostavka.by/products/…','saved_url':None}}
    snapshots={tid:{'provider':m['provider'],'source':m['source'],'name':'Молоко 900 мл','price':'2.79','regular_price':'3.49','unit':'шт.','available':True,'normalized':'','conditions':'Публичная цена сайта · магазин по умолчанию','url':m['saved_url'] or 'https://sosedi-dostavka.by/products/moloko-456','comparison_key':tid} for tid,m in meta.items()}
    data={'enabled':True,'telegram_connected':True,'supported_offer_ids':[501,502],'supported_offers':meta,'offers':[]}
    def route(r,req):
        path=urlparse(req.url).path
        if path.endswith('/catalog-watches'):
            return r.fulfill(json={'tracked_count':1,'offers':[],'events':[dict(s,product_id=401,product_name='Молоко',old_price='3.49',percent='-20.1',direction='down',created_at='2026-10-16T10:00:00Z') for s in snapshots.values()],'unlinked':[]})
        if path.endswith('/preview'):
            return r.fulfill(json=next(s for s in snapshots.values() if s['url']==req.post_data_json['url']))
        if req.method=='PUT':
            writes.append(req.post_data_json);tid=path.rsplit('/',1)[1]
            data['offers'].append({'template_id':int(tid),'snapshot':snapshots[tid],'checked_at':'2026-10-16T10:00:00Z'})
        return r.fulfill(json=data)
    p.route(re.compile(r'.*/api/v1/catalog-watches(?:/.*)?$'),route)
    setup(p,static_server_url,width,many=True);p.locator('[data-product-tab=offers]').click()
    green=p.locator('[data-offer-watch="501"]');sosedi=p.locator('[data-offer-watch="502"]')
    expect(green.locator('[data-watch-search]')).to_have_count(0)
    expect(green).to_contain_text('Green · цена на сайте');expect(sosedi).to_contain_text('Соседи · цена на сайте')
    green.locator('[data-watch-saved]').click();expect(green.locator('[data-watch-confirm]')).to_be_visible();assert writes==[]
    green.locator('[data-watch-confirm]').click();expect(green.locator('[data-watch-remove]')).to_be_visible()
    sosedi.locator('[data-watch-url]').fill(snapshots['502']['url']);sosedi.locator('[data-watch-preview]').click()
    sosedi.locator('[data-watch-confirm]').click();expect(sosedi.locator('[data-watch-remove]')).to_be_visible()
    for host in [green,sosedi]:
        assert host.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
        expect(host).not_to_contain_text('Е-доставка')
    sosedi.scroll_into_view_if_needed();p.screenshot(path=f'/tmp/fa-multi-watch-{width}.png')
    p.locator('#closeCatalogProductModalBtn').click()
    dashboard=p.locator('#dashboardProductWatches');expect(dashboard).to_contain_text('Green');expect(dashboard).to_contain_text('Соседи');expect(dashboard).not_to_contain_text('Е-доставка')
    assert len(writes)==2
