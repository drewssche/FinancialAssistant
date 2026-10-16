from urllib.parse import urlparse
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login

CODE='4006381333931'


def setup(page,url,width,*,many=False):
    page.set_viewport_size({'width':width,'height':1100})
    product={'id':401,'name':'Молоко','sale_unit':'pack','package_quantity':'900','package_unit':'ml','offers':[{'id':501,'template_id':501,'source_id':301,'name':'Молоко','source_name':'Green'}]}
    data={'variants':[{'id':41,'name':'900 мл','sale_unit':'pack','package_quantity':'900','package_unit':'ml','codes':[CODE]}],'offers':[{'template_id':501,'retailer_code':'000-42'}]}
    if many:
        product['offers'].append({'id':502,'template_id':502,'source_id':302,'name':'Молоко','source_name':'Соседи'})
        data['variants'].append({'id':42,'name':'1 л','sale_unit':'pack','package_quantity':'1','package_unit':'l','codes':[]})
        data['offers'].append({'template_id':502,'retailer_code':'002'})
    writes=[]
    def handler(route,req):
        path=urlparse(req.url).path
        if req.method in ('POST','PATCH') and (path.endswith('/401') or path.endswith('/catalog-products')):
            writes.append(req.post_data_json);return route.fulfill(json={**product,**req.post_data_json})
        if path.endswith('/identity'):result=data
        elif path.endswith('/401'):result=product
        elif path.endswith('/catalog-products'):result={'items':[product],'total':1,'page':1,'page_size':100}
        else:return route.fallback()
        route.fulfill(json=result)
    page.route('**/api/v1/operations/**',handler)
    page.route('**/package-replacements',lambda r:r.fulfill(json={'variants':[],'items':[]}))
    page.goto(f'{url}/static/index.html');page.evaluate("window.Telegram={WebApp:{initData:'mock-init-data',ready(){},expand(){}}}");_login(page)
    page.evaluate("window.App.getRuntimeModule('catalog-products').openEditor(401)")
    return writes



def card(p,id=501):return p.locator(f'[data-modal-offer-id="{id}"]')
def barcode(p,id=501):return card(p,id).locator('[data-code=barcode]')
def sku(p,id=501):return card(p,id).locator('[data-code=sku]')


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_codes_in_source_cards_only_and_save_together(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,width)
    expect(p.locator('#catalogProductForm [data-code]')).to_have_count(0)
    expect(barcode(p)).not_to_be_visible()
    p.locator('[data-product-tab=offers]').click()
    expect(barcode(p)).to_have_value(CODE);expect(sku(p)).to_have_value('000-42')
    barcode(p).fill('0'+CODE);sku(p).fill('000-43')
    p.locator('[data-product-tab=product]').click();p.locator('#catalogProductName').fill('Молоко новое')
    p.locator('[data-product-tab=offers]').click()
    expect(barcode(p)).to_have_value('0'+CODE);expect(sku(p)).to_have_value('000-43')
    for field in [barcode(p),sku(p)]:
        box=field.bounding_box();assert box['x']>=0 and box['x']+box['width']<=width+1
    card(p).scroll_into_view_if_needed();p.screenshot(path=f'/tmp/fa-offer-codes-{width}.png')
    assert writes==[]
    footer=p.locator('.catalog-product-modal-footer').bounding_box();save=p.locator('#submitCatalogProductBtn').bounding_box()
    assert save['x']+save['width']>footer['x']+footer['width']-24
    p.locator('#submitCatalogProductBtn').click();expect(p.locator('#catalogProductModal')).to_be_hidden()
    assert writes[-1]['name']=='Молоко новое'
    assert writes[-1]['codes']=={'barcodes':[{'variant_id':41,'codes':['0'+CODE]}],'retailers':[{'template_id':501,'retailer_code':'000-43'}]}


@pytest.mark.e2e
def test_shared_barcode_but_independent_store_skus(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,390,many=True)
    p.locator('[data-product-tab=offers]').click()
    expect(barcode(p,502)).to_have_value(CODE)
    barcode(p).fill('0'+CODE);expect(barcode(p,502)).to_have_value('0'+CODE)
    sku(p).fill('00043');expect(sku(p,502)).to_have_value('002')
    sku(p,502).fill('003');expect(sku(p)).to_have_value('00043')
    p.locator('#submitCatalogProductBtn').click();expect(p.locator('#catalogProductModal')).to_be_hidden()
    assert writes[-1]['codes']=={'barcodes':[{'variant_id':41,'codes':['0'+CODE]}],'retailers':[{'template_id':501,'retailer_code':'00043'},{'template_id':502,'retailer_code':'003'}]}


@pytest.mark.e2e
def test_cancel_and_new_product_no_code_form(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,390)
    p.locator('[data-product-tab=offers]').click();expect(barcode(p)).to_have_value(CODE)
    sku(p).fill('999');p.locator('#closeCatalogProductModalBtn').click()
    p.evaluate("window.App.getRuntimeModule('catalog-products').openEditor(401)")
    p.locator('[data-product-tab=offers]').click();expect(sku(p)).to_have_value('000-42')
    assert writes==[]
    p.locator('#closeCatalogProductModalBtn').click();p.evaluate("window.App.getRuntimeModule('catalog-products').openEditor()")
    expect(p.locator('#catalogProductForm [data-code]')).to_have_count(0)
    p.locator('#catalogProductName').fill('Новый товар');p.locator('#submitCatalogProductBtn').click()
    expect(p.locator('#catalogProductModal')).to_be_hidden();assert 'codes' not in writes[-1]


@pytest.mark.e2e
def test_invalid_barcode_blocks_save_in_offers_tab(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,390)
    p.locator('[data-product-tab=offers]').click();expect(barcode(p)).to_have_value(CODE)
    barcode(p).fill('123');p.locator('#submitCatalogProductBtn').click()
    expect(p.get_by_text('Проверьте штрихкод:',exact=False)).to_be_visible();assert writes==[]
    barcode(p).fill(CODE);sku(p).fill('0009');p.locator('#submitCatalogProductBtn').click()
    expect(p.locator('#catalogProductModal')).to_be_hidden()
    assert writes[-1]['codes']['retailers']==[{'template_id':501,'retailer_code':'0009'}]


@pytest.mark.e2e
def test_code_load_failure_retry_preserves_product_draft(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;setup(p,static_server_url,390)
    p.locator('[data-product-tab=offers]').click();expect(barcode(p)).to_have_value(CODE)
    p.route('**/catalog-products/401/identity',lambda r:r.fulfill(status=500,json={'detail':'offline'}))
    p.evaluate("window.App.getRuntimeModule('catalog-product-codes').reload()")
    expect(p.locator('#catalogProductCodesRetry')).to_be_visible();expect(barcode(p)).to_be_disabled()
    p.locator('[data-product-tab=product]').click();p.locator('#catalogProductName').fill('Несохранённое имя')
    p.unroute('**/catalog-products/401/identity');p.locator('[data-product-tab=offers]').click();p.locator('#catalogProductCodesRetry').click()
    expect(barcode(p)).to_be_enabled();expect(barcode(p)).to_have_value(CODE)
    p.locator('[data-product-tab=product]').click();expect(p.locator('#catalogProductName')).to_have_value('Несохранённое имя')


@pytest.mark.e2e
def test_linked_offer_size_keeps_its_own_barcode(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,1440,many=True)
    expect(barcode(p)).to_have_value(CODE)
    p.route('**/catalog-products/401/identity',lambda r:r.fulfill(json={'variants':[
        {'id':41,'name':'900 мл','sale_unit':'pack','package_quantity':'900','package_unit':'ml','codes':[CODE]},
        {'id':42,'name':'1 л','sale_unit':'pack','package_quantity':'1','package_unit':'l','codes':['5901234123457']}],
        'offers':[{'template_id':501,'variant_id':41,'retailer_code':'001'},{'template_id':502,'variant_id':42,'retailer_code':'002'}]}))
    p.evaluate("window.App.getRuntimeModule('catalog-product-codes').reload()")
    p.locator('[data-product-tab=offers]').click();expect(barcode(p,502)).to_have_value('5901234123457')
    barcode(p).fill('0'+CODE);expect(barcode(p,502)).to_have_value('5901234123457')
    p.locator('#submitCatalogProductBtn').click();expect(p.locator('#catalogProductModal')).to_be_hidden()
    assert writes[-1]['codes']['barcodes']==[{'variant_id':41,'codes':['0'+CODE]}]


@pytest.mark.e2e
def test_missing_product_name_returns_to_main_tab_without_losing_codes(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,390)
    p.locator('#catalogProductName').fill('')
    p.locator('[data-product-tab=offers]').click();expect(sku(p)).to_have_value('000-42')
    sku(p).fill('000-43');p.locator('#submitCatalogProductBtn').click()
    expect(p.locator('#catalogProductName')).to_be_visible();assert writes==[]
    p.locator('#catalogProductName').fill('Молоко')
    p.locator('[data-product-tab=offers]').click();expect(sku(p)).to_have_value('000-43')
    p.locator('#submitCatalogProductBtn').click();expect(p.locator('#catalogProductModal')).to_be_hidden()
