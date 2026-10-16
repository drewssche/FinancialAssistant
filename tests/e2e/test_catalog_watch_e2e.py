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
    host.locator('input').fill(s['url']);host.locator('[data-watch-preview]').click()
    expect(host.get_by_text('Молоко 900 мл',exact=True)).to_be_visible()
    assert len(writes)==1
    host.locator('[data-watch-confirm]').click();expect(host.locator('[data-watch-remove]')).to_be_visible()
    assert writes[-1]['expected_key']=='test'
    host.scroll_into_view_if_needed()
    box=host.bounding_box();assert box['x']>=0 and box['x']+box['width']<=width+1
    p.screenshot(path=f'/tmp/fa-watch-{width}.png')
    toggle.uncheck();expect(toggle).not_to_be_checked()
    host.locator('[data-watch-remove]').click();expect(host.locator('input')).to_be_visible()
    assert data['offers']==[]
    p.locator('#closeCatalogProductModalBtn').click()
    expect(p.locator('#dashboardProductWatches')).to_contain_text('Включите «Следить за ценой»')
