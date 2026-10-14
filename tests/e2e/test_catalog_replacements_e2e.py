from urllib.parse import urlparse
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_confirm_replacement_prices_undo_and_draft_safety(static_server_url,page_with_receipt_api_mock,width):
    page=page_with_receipt_api_mock;page.set_viewport_size({'width':width,'height':1100})
    product={'id':401,'name':'Молоко','offers':[]}
    a=dict(id=91,name='1 л',sale_unit='pack',package_quantity='1',package_unit='l',codes=[])
    b=dict(id=92,name='900 мл',sale_unit='pack',package_quantity='900',package_unit='ml',codes=[])
    data={'variants':[a,b],'items':[]}; requests=[];writes=[];errors=[];state={'fail':False,'hold':False,'pending':None}
    page.on('pageerror',lambda e:errors.append(str(e)))
    pair=dict(currency='BYN',shop_name='Магазин',old=dict(operation_id=777,recorded_at='2026-10-01',price='3',normalized_price='3',is_discounted=False),new=dict(operation_id=778,recorded_at='2026-10-03',price='3',normalized_price='3.333333',is_discounted=True),package_price_change_percent='0.00',normalized_price_change_percent='11.11',regular_normalized_change_percent=None)
    def handler(route,req):
        path=urlparse(req.url).path
        if '/package-replacements' in path:
            requests.append((req.method,path))
            if state['hold'] and req.method=='GET':state['pending']=route;return
            if state['fail']:return route.fulfill(status=503,json={'detail':'Временно недоступно'})
            if req.method=='POST':
                payload=req.post_data_json;writes.append(payload)
                data['items']=[dict(id=1,old_variant_id=91,new_variant_id=92,effective_date=payload['effective_date'],old_snapshot=a.copy(),new_snapshot=b.copy(),note=payload['note'],unit='l',old_volume='1',new_volume='0.9',volume_change_percent='-10.00',constant_package_price_change_percent='11.11',comparisons=[pair])]
            if req.method=='DELETE':data['items']=[]
            return route.fulfill(json=data)
        if path.endswith('/777'):
            return route.fulfill(json={'id':777,'kind':'expense','amount':'3','original_amount':'3','currency':'BYN','operation_date':'2026-10-01','receipt_items':[]})
        if path.endswith('/401'):result=product
        elif path.endswith('/402'):result={**product,'id':402,'name':'Другой товар'}
        elif path.endswith('/catalog-products'):result={'items':[product],'total':1,'page':1,'page_size':100}
        else:return route.fallback()
        route.fulfill(json=result)
    page.route('**/api/v1/operations/**',handler)
    page.route('**/identity', lambda r:r.fulfill(json={'variants':[], 'offers':[]}))
    page.goto(f'{static_server_url}/static/index.html')
    page.evaluate("window.Telegram={WebApp:{initData:'mock-init-data',ready(){},expand(){}}}")
    _login(page)
    page.evaluate("window.App.getRuntimeModule('catalog-products').openEditor(401)")
    page.locator('#catalogProductName').fill('Несохранённое название')
    assert requests==[]
    page.locator('[data-product-tab="packages"]').click()
    page.locator('[data-package-task="replacements"]').click()
    old=page.locator('#catalogReplacementOld');new=page.locator('#catalogReplacementNew')
    expect(old.locator('option')).to_have_count(3)
    old.select_option('91');new.select_option('92')
    page.locator('#catalogReplacementDate').fill('2026-10-02')
    page.locator('#catalogReplacementNote').fill('В магазине появилась меньшая упаковка')
    submit=page.locator('#catalogReplacementForm button[type="submit"]')
    submit.click();assert writes==[]
    page.locator('#catalogReplacementConfirmed').check()
    new.select_option('91')
    expect(page.locator('#catalogReplacementConfirmed')).not_to_be_checked()
    new.select_option('92')
    page.locator('#catalogReplacementConfirmed').check();submit.click()
    card=page.locator('.catalog-replacement-card').first
    expect(card).to_contain_text('-10%')
    expect(card).to_contain_text('+11,11%')
    expect(card).to_contain_text('Это расчёт, а не наблюдение цены')
    expect(card).to_contain_text('Обычная цена за л: нет данных')
    expect(page.locator('#catalogProductName')).to_have_value('Несохранённое название')
    assert writes[0]['confirmed'] is True and writes[0]['expected_old']['package_quantity']=='1'
    for selector in ['#catalogReplacementForm','.catalog-replacement-card','#catalogReplacementOld']:
        box=page.locator(selector).bounding_box();assert box['x']>=0 and box['x']+box['width']<=width+1
    page.locator('#catalogReplacementsDetails').scroll_into_view_if_needed()
    page.screenshot(path=f'/tmp/fa-replacements-{width}.png')
    card.locator('[data-product-purchase-id="777"]').click()
    expect(page.locator('#editModal')).to_be_visible()
    page.click('#closeEditModalBtn')
    expect(card.locator('[data-product-purchase-id="777"]')).to_be_focused()
    # Related edits invalidate comparison, but retain unsaved form data.
    page.locator('#catalogReplacementNote').fill('Черновик следующей замены')
    page.evaluate("window.App.getRuntimeModule('catalog-replacements').refresh({id:401,offers:[]})")
    expect(page.locator('#catalogReplacementNote')).to_have_value('Черновик следующей замены')
    page.evaluate("document.dispatchEvent(new CustomEvent('app:activity-changed',{detail:{method:'PATCH',path:'/api/v1/operations/777'}}))")
    expect(page.locator('#catalogReplacementsList')).to_contain_text('Данные изменились')
    expect(page.locator('#catalogReplacementNote')).to_have_value('Черновик следующей замены')
    state['fail']=True;page.click('#catalogReplacementsRefresh')
    expect(page.locator('#catalogReplacementsStatus')).to_contain_text('Не удалось загрузить')
    state['fail']=False;page.click('#catalogReplacementsRefresh')
    expect(card).to_be_visible()
    card.locator('[data-product-purchase-id="777"]').click()
    expect(page.locator('#editModal')).to_be_visible()
    page.evaluate("document.dispatchEvent(new CustomEvent('app:activity-changed',{detail:{method:'PATCH',path:'/api/v1/operations/777'}}))")
    page.click('#closeEditModalBtn')
    expect(page.locator('#catalogReplacementsRefresh')).to_be_focused()
    expect(page.locator('#catalogReplacementsList')).to_contain_text('Данные изменились')
    page.click('#catalogReplacementsRefresh');expect(card).to_be_visible()

    remove=card.locator('[data-replacement-remove]');remove.click()
    assert not any(method=='DELETE' for method,path in requests)
    remove.click();expect(page.locator('#catalogReplacementsList')).to_contain_text('Подтверждённых замен пока нет')
    expect(page.locator('#catalogProductName')).to_have_value('Несохранённое название')
    # A delayed response for an old product must never populate the next product.
    state['hold']=True;page.click('#catalogReplacementsRefresh')
    page.click('#closeCatalogProductModalBtn')
    page.evaluate("window.App.getRuntimeModule('catalog-products').openEditor(402)")
    state['pending'].fulfill(json=data)
    expect(page.locator('#catalogReplacementsBody')).to_be_hidden()
    assert errors==[]
