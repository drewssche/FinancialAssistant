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


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_codes_visible_on_product_tab_and_save_with_product(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,width)
    expect(p.locator('#catalogProductBarcode')).to_be_visible();expect(p.locator('#catalogProductBarcode')).to_have_value(CODE)
    expect(p.locator('#catalogProductSku')).to_have_value('000-42')
    expect(p.locator('#catalogProductCodeVariant')).to_be_hidden();expect(p.locator('#catalogProductCodeOffer')).to_be_hidden()
    p.locator('#catalogProductBarcode').fill('0'+CODE);p.locator('#catalogProductSku').fill('000-43')
    p.locator('#catalogProductName').fill('Молоко новое')
    p.locator('[data-product-tab=offers]').click();p.locator('[data-product-tab=product]').click()
    expect(p.locator('#catalogProductSku')).to_have_value('000-43')
    for selector in ['#catalogProductBarcode','#catalogProductSku','#catalogProductCodeOfferHint']:
        box=p.locator(selector).bounding_box();assert box['x']>=0 and box['x']+box['width']<=width+1
    p.locator('.catalog-product-codes').scroll_into_view_if_needed();p.screenshot(path=f'/tmp/fa-primary-codes-{width}.png')
    assert writes==[]
    p.locator('#submitCatalogProductBtn').click()
    expect(p.locator('#catalogProductModal')).to_be_hidden()
    assert writes[-1]['name']=='Молоко новое'
    assert writes[-1]['codes']=={'barcodes':[{'variant_id':41,'codes':['0'+CODE]}],'retailers':[{'template_id':501,'shop_name':'','retailer_code':'000-43'}]}


@pytest.mark.e2e
def test_multiple_packages_and_stores_keep_separate_drafts_and_cancel(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,390,many=True)
    expect(p.locator('#catalogProductBarcode')).to_have_value(CODE)
    expect(p.locator('#catalogProductCodeVariant')).to_be_hidden()
    expect(p.locator('#catalogProductSku')).to_be_disabled()
    size=p.locator('.catalog-product-measurements .measurement-editor input')
    size.fill('800')
    expect(p.locator('#catalogProductBarcode')).to_have_value('')
    size.fill('900')
    expect(p.locator('#catalogProductBarcode')).to_have_value(CODE)
    p.locator('#catalogProductCodeOffer').select_option('501');p.locator('#catalogProductSku').fill('00043')
    p.locator('#catalogProductCodeOffer').select_option('502');expect(p.locator('#catalogProductSku')).to_have_value('002')
    p.locator('#catalogProductCodeOffer').select_option('501');expect(p.locator('#catalogProductSku')).to_have_value('00043')
    p.locator('#closeCatalogProductModalBtn').click()
    assert writes==[]
    p.evaluate("window.App.getRuntimeModule('catalog-products').openEditor(401)")
    expect(p.locator('#catalogProductBarcode')).to_have_value(CODE)
    p.locator('#catalogProductCodeOffer').select_option('501');expect(p.locator('#catalogProductSku')).to_have_value('000-42')


@pytest.mark.e2e
def test_new_product_supports_barcode_and_shop_sku_without_tabs(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,390)
    p.locator('#closeCatalogProductModalBtn').click();p.evaluate("window.App.getRuntimeModule('catalog-products').openEditor()")
    expect(p.locator('#catalogProductCodeVariant')).to_be_hidden()
    p.locator('#catalogProductName').fill('Новый товар');p.locator('#catalogProductBarcode').fill(CODE)
    p.locator('.catalog-product-measurements .measurement-editor input').fill('250')
    p.locator('.catalog-product-measurements [data-unit=g]').click()
    expect(p.locator('#catalogProductBarcode')).to_have_value(CODE)
    p.locator('#catalogProductSku').fill('000123');p.locator('#catalogProductCodeShop').fill('Green')
    p.locator('#submitCatalogProductBtn').click();expect(p.locator('#catalogProductModal')).to_be_hidden()
    assert writes[-1]['codes']=={'barcodes':[{'variant_id':None,'codes':[CODE]}],'retailers':[{'template_id':None,'retailer_code':'000123','shop_name':'Green'}]}


@pytest.mark.e2e
def test_invalid_code_does_not_save_and_single_store_can_change(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,390)
    expect(p.locator('#catalogProductBarcode')).to_have_value(CODE)
    p.locator('#catalogProductCodeOfferHint button').click();p.locator('#catalogProductCodeOffer').select_option('new')
    p.locator('#catalogProductSku').fill('0009');p.locator('#catalogProductCodeShop').fill('Соседи')
    p.locator('#catalogProductBarcode').fill('123')
    p.locator('#submitCatalogProductBtn').click()
    expect(p.get_by_text('Проверьте штрихкод:',exact=False)).to_be_visible()
    assert writes==[]
    p.locator('#catalogProductBarcode').fill(CODE);p.locator('#submitCatalogProductBtn').click()
    expect(p.locator('#catalogProductModal')).to_be_hidden()
    assert writes[-1]['codes']['retailers']==[{'template_id':None,'shop_name':'Соседи','retailer_code':'0009'}]


@pytest.mark.e2e
def test_code_load_failure_retry_preserves_product_draft(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;setup(p,static_server_url,390)
    expect(p.locator('#catalogProductBarcode')).to_have_value(CODE)
    p.route('**/catalog-products/401/identity',lambda r:r.fulfill(status=500,json={'detail':'offline'}))
    p.evaluate("window.App.getRuntimeModule('catalog-product-codes').reload()")
    expect(p.locator('#catalogProductCodesRetry')).to_be_visible()
    expect(p.locator('#catalogProductBarcode')).to_be_disabled()
    p.locator('#catalogProductName').fill('Несохранённое имя')
    p.unroute('**/catalog-products/401/identity')
    p.locator('#catalogProductCodesRetry').click()
    expect(p.locator('#catalogProductBarcode')).to_be_enabled()
    expect(p.locator('#catalogProductBarcode')).to_have_value(CODE)
    expect(p.locator('#catalogProductName')).to_have_value('Несохранённое имя')
