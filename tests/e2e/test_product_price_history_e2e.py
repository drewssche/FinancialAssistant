from urllib.parse import urlparse, parse_qs

import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1440])
def test_price_graph_filters_receipt_link_and_draft(static_server_url, page_with_receipt_api_mock, width):
    page=page_with_receipt_api_mock
    page.set_viewport_size({'width':width,'height':1050})
    errors,queries=[],[]
    page.on('pageerror',lambda err: errors.append(str(err)))
    product={'id':401,'name':'Молоко','offers':[{'id':501,'name':'Молоко','source_name':'Green'}]}
    rows=[dict(operation_id=i+1,receipt_item_id=i+1,recorded_at=f'2026-10-0{i+1}',price=str(price),change_percent=change,direction=direction,package_quantity='900',package_unit='ml',sale_unit='pack',is_discounted=i==2,package_changed=False) for i,(price,change,direction) in enumerate([(3,None,0),(4,'33.33',1),(3,'-25',-1)])]
    def handler(route,req):
        path=urlparse(req.url).path
        if path.endswith('/catalog-products'): result={'items':[product], 'total':1, 'page':1, 'page_size':100}
        elif path.endswith('/401'): result=product
        elif path.endswith('/price-observations'):
            query=parse_qs(urlparse(req.url).query);queries.append(query)
            if query['price_kind']==['regular']: result={'series':[],'excluded_count':3}
            else:
                group={'currency':'BYN','shop_name':'Green','unit':'pack','package_quantity':'900','package_unit':'ml','observations':rows,'change_percent':'0','increases':1,'decreases':1}
                result={'basis':'unit','price_kind':'paid','series':[group,dict(group,currency='USD')], 'excluded_count':1}
        elif path.endswith('/operations/3'): result={'id':3,'kind':'expense','amount':'3','original_amount':'3','currency':'BYN','operation_date':'2026-10-03','receipt_items':[]}
        else: return route.fallback()
        route.fulfill(json=result)
    page.route('**/api/v1/operations/**', handler)
    page.goto(f'{static_server_url}/static/index.html')
    page.evaluate("window.Telegram = {WebApp: {initData: 'mock-init-data', ready() {}, expand() {}}}")
    _login(page)
    page.evaluate("window.App.getRuntimeModule('catalog-products').openEditor(401)")
    page.locator('#catalogProductName').fill('Мой черновик')
    page.locator('[data-product-tab="prices"]').click()
    expect(page.locator('#catalogProductPriceMode')).to_have_value('purchases')
    expect(page.locator('.product-price-summary')).to_contain_text('0%')
    expect(page.locator('.product-price-events')).to_contain_text('+33,33%')
    expect(page.locator('.product-price-events')).to_contain_text('-25%')
    expect(page.locator('.product-price-chart circle')).to_have_count(3)
    for selector in ['.product-price-chart', '#catalogProductHistoryControls', '.product-price-events']:
        box=page.locator(selector).bounding_box()
        assert box['x']>=0 and box['x']+box['width']<=width+1
    chart=page.locator('.product-price-chart')
    # Smoothing must pass through observations and never overshoot their range.
    assert chart.locator('.product-price-line').evaluate("""path=>{
      const n=path.getTotalLength();
      for(let i=0;i<=200;i++){const p=path.getPointAtLength(n*i/200);if(p.y<40-.01||p.y>135+.01)return false;}
      return path.getAttribute('d').includes('C');
    }""")
    chart.focus();chart.press('ArrowRight')
    tip=page.locator('.product-price-chart-host .analytics-chart-tooltip')
    expect(tip).to_be_visible();expect(tip).to_contain_text('+33,33%')
    chart.press('End');expect(tip).to_contain_text('-25%')
    chart.press('Escape');expect(tip).to_have_class('analytics-chart-tooltip hidden')
    bounds=chart.bounding_box()
    chart.dispatch_event('pointerdown',{'pointerType':'touch','clientX':bounds['x']+bounds['width']-12,'clientY':bounds['y']+30})
    chart.dispatch_event('pointerleave',{'pointerType':'touch'})
    expect(tip).to_be_visible();expect(tip).to_contain_text('-25%')
    # Nearest purchase is selected across the full chart, without aiming at a dot.
    chart.hover(position={'x':chart.bounding_box()['width']/2,'y':20})
    expect(tip).to_contain_text('+33,33%')
    box=tip.bounding_box();host=page.locator('.product-price-chart-host').bounding_box()
    assert box['x']>=host['x'] and box['x']+box['width']<=host['x']+host['width']+1
    page.screenshot(path=f'/tmp/fa-price-history-{width}.png',full_page=False)
    page.locator('#catalogProductPriceSeries').select_option('1')
    expect(page.locator('.product-price-events')).to_contain_text('USD')
    page.locator('[data-product-purchase-id="3"]').click()
    expect(page.locator('#editModal')).to_be_visible()
    page.evaluate("document.dispatchEvent(new CustomEvent('app:activity-changed', {detail:{method:'PATCH',path:'/api/v1/operations/3'}}))")
    page.locator('#closeEditModalBtn').click()
    expect(page.locator('[data-product-purchase-id="3"]')).to_be_focused()
    expect(page.locator('#catalogProductPriceSeries')).to_have_value('1')
    page.click('#catalogProductConditionsButton')
    page.locator('#catalogProductPriceBasis').select_option('normalized')
    page.locator('#catalogProductPriceFrom').fill('2026-10-02')
    page.locator('#catalogProductPriceTo').fill('2026-10-03')
    page.locator('#catalogProductPriceTo').blur()
    page.wait_for_function("document.querySelector('.product-price-chart') !== null")
    assert queries[-1]['basis']==['normalized'] and queries[-1]['date_from']==['2026-10-02'] and queries[-1]['date_to']==['2026-10-03']
    page.locator('#catalogProductPriceKind').select_option('regular')
    page.locator('#catalogProductConditionsDialog').get_by_role('button',name='Закрыть настройки').click()
    expect(page.locator('#catalogProductPricesList')).to_contain_text('Нет покупок')
    expect(page.locator('#catalogProductPricesList')).to_contain_text('Не показано позиций: 3')
    page.locator('[data-product-tab="product"]').click()
    expect(page.locator('#catalogProductName')).to_have_value('Мой черновик')
    assert errors==[]
