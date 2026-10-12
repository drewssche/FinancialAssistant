from urllib.parse import urlparse, parse_qs
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320,390,1440])
def test_lazy_price_changes_filters_pagination_history_and_cleanup(static_server_url,page_with_receipt_api_mock,width):
    page=page_with_receipt_api_mock;page.set_viewport_size({'width':width,'height':1050})
    requests=[];histories=[];errors=[];fail=[False]
    page.on('pageerror',lambda e:errors.append(str(e)))
    product={'id':401,'name':'Молоко','offers':[{'id':501,'name':'Молоко магазин','source_name':'Green'}]}
    row=dict(product_id=401,product_name='Молоко',template_id=501,offer_name='Молоко магазин',shop_name='Green',currency='BYN',unit='l',
        sale_unit=None,package_quantity=None,package_unit=None,observations_count=3,increases=1,decreases=1,package_changed=True,
        reference_price='3',latest_price='3',reference_date='2026-10-01',latest_date='2026-10-03',latest_operation_id=777,latest_receipt_item_id=1,
        direction=0,change_percent='0',period_change_percent='0',last_change_percent='-25',baseline_cost='6',latest_cost='6',cost_difference='0',
        latest_is_discounted=True,reference_is_discounted=False)
    def handler(route,req):
        path=urlparse(req.url).path;query=parse_qs(urlparse(req.url).query)
        if path.endswith('/price-changes'):
            requests.append(query)
            if fail[0]:return route.fulfill(status=503,json={'detail':'Временная ошибка'})
            index=int(query.get('page',['1'])[0]);values=[dict(row,product_name=f'Молоко {i}') for i in range(20)] if index==1 else [dict(row,product_name='Последняя строка')]
            return route.fulfill(json={'items':values,'total':21,'page':index,'page_size':20,'excluded_count':2,'insufficient_series_count':1})
        if path.endswith('/price-observations'):
            histories.append(query)
            group = dict(unit='l', shop_name='Green', package_quantity=None, package_unit=None, sale_unit=None,
                change_percent='0', increases=1, decreases=1, observations=[dict(receipt_item_id=1, operation_id=777,
                recorded_at='2026-10-03', price='3', change_percent='0', direction=0, sale_unit='l', package_quantity=None,
                package_unit=None, is_discounted=False, package_changed=False)])
            return route.fulfill(json={'basis':'normalized','price_kind':'paid','series':[dict(group,currency='USD'),dict(group,currency='BYN')],'excluded_count':0})
        if path.endswith('/401'):return route.fulfill(json=product)
        if path.endswith('/catalog-products'):return route.fulfill(json={'items':[product],'total':1,'page':1,'page_size':100})
        route.fallback()
    page.route('**/api/v1/operations/**',handler)
    page.goto(f'{static_server_url}/static/index.html')
    page.evaluate("window.Telegram={WebApp:{initData:'mock-init-data',ready(){},expand(){}}}")
    _login(page)
    page.evaluate("window.App.getRuntimeModule('navigation').switchSection('item_catalog')")
    expect(page.locator('[data-catalog-product-id="401"]')).to_be_visible()
    assert requests==[]
    page.locator('#catalogPriceChanges > summary').click()
    expect(page.locator('.catalog-price-change')).to_have_count(20)
    expect(page.locator('.catalog-price-change').first).to_contain_text('последний шаг: -25%')
    expect(page.locator('.catalog-price-change').first).to_contain_text('Замена упаковки не подтверждена')
    page.locator('#catalogPriceChangesMore').click()
    expect(page.locator('.catalog-price-change')).to_have_count(21)
    expect(page.locator('#catalogPriceChangesMore')).to_be_hidden()
    page.locator('.catalog-price-changes-options > summary').click()
    form=page.locator('#catalogPriceChangesForm')
    form.locator('[name="q"]').fill('vjkjrj')
    form.locator('[name="basis"]').select_option('normalized')
    form.locator('[name="comparison"]').select_option('previous')
    form.locator('[name="direction"]').select_option('down')
    form.locator('[name="date_from"]').fill('2026-10-01')
    expect(page.locator('#catalogPriceChangesStatus')).to_contain_text('изменились')
    form.locator('button[type="submit"]').click()
    expect(page.locator('.catalog-price-change')).to_have_count(20)
    assert requests[-1]['q']==['vjkjrj'] and requests[-1]['basis']==['normalized'] and requests[-1]['page']==['1']
    for control in form.locator('input,select,button').all():
        box=control.bounding_box();assert box['x']>=0 and box['x']+box['width']<=width+1
    page.locator('.catalog-price-change').first.scroll_into_view_if_needed()
    page.screenshot(path=f'/tmp/fa-price-changes-{width}.png')
    for card in page.locator('.catalog-price-change').all():
        size=card.evaluate('n=>({width:n.clientWidth,scroll:n.scrollWidth})');assert size['scroll']<=size['width']+1
    page.locator('[data-open-price-change="0"]').click()
    expect(page.locator('#catalogProductModal')).to_be_visible()
    expect(page.locator('#catalogProductPriceBasis')).to_have_value('normalized')
    expect(page.locator('#catalogProductPriceFrom')).to_have_value('2026-10-01')
    expect(page.locator('#catalogProductPriceSeries')).to_have_value('1')
    expect(page.locator('.product-price-chart')).to_have_attribute('aria-label','Оплаченная цена: BYN · Green · за л')
    assert histories[-1]['basis']==['normalized'] and histories[-1]['date_from']==['2026-10-01']
    page.locator('#closeCatalogProductModalBtn').click()
    expect(page.locator('[data-open-price-change="0"]')).to_be_focused()
    page.evaluate("window.App.getRuntimeModule('catalog-products').invalidateLocal()")
    expect(page.locator('#catalogPriceChangesStatus')).to_contain_text('изменились')
    fail[0]=True
    form.locator('button[type="submit"]').click()
    expect(page.locator('#catalogPriceChangesStatus')).to_contain_text('Не удалось загрузить')
    fail[0]=False
    form.locator('button[type="submit"]').click()
    expect(page.locator('.catalog-price-change')).to_have_count(20)
    page.evaluate("window.App.getRuntimeModule('catalog-products').cleanupRuntime()")
    expect(page.locator('#catalogPriceChanges')).not_to_have_attribute('open','')
    expect(page.locator('.catalog-price-change')).to_have_count(0)
    assert errors==[]
