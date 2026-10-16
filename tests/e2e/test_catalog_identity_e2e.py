from urllib.parse import urlparse
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_variant_codes_offer_mapping_and_parent_draft(static_server_url,page_with_receipt_api_mock,width):
    page=page_with_receipt_api_mock;page.set_viewport_size({'width':width,'height':1100})
    product={'id':401,'name':'Молоко','offers':[{'id':501,'name':'Молоко 900 мл','source_name':'Green'}]}
    data={'variants':[],'offers':[]}; writes=[];errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    def handler(route,req):
        path=urlparse(req.url).path
        if req.method in ('POST','PUT'):
            payload=req.post_data_json;writes.append((path,payload))
            if '/variants' in path:
                data['variants']=[dict(payload,id=1)]
            elif '/identity' in path:
                data['offers']=[dict(payload,template_id=501)]
            else: return route.fallback()
            return route.fulfill(json=data)
        if path.endswith('/identity'): result=data
        elif path.endswith('/401'):result=product
        elif path.endswith('/catalog-products'):result={'items':[product],'total':1,'page':1,'page_size':100}
        else:return route.fallback()
        route.fulfill(json=result)
    page.route('**/api/v1/operations/**',handler)
    page.route('**/package-replacements', lambda r:r.fulfill(json={'variants':[], 'items':[]}))
    page.goto(f'{static_server_url}/static/index.html')
    page.evaluate("window.Telegram = {WebApp:{initData:'mock-init-data',ready(){},expand(){}}}")
    _login(page)
    page.evaluate("window.App.getRuntimeModule('catalog-products').openEditor(401)")
    page.locator('#catalogProductName').fill('Мой несохранённый товар')
    page.locator('[data-product-tab="packages"]').click()
    page.locator('#catalogVariantAdd').click()
    page.locator('#catalogVariantName').fill('Пакет 900 мл')
    page.locator('#catalogVariantForm .measurement-editor input').fill('900')
    page.locator('#catalogVariantForm [data-unit="ml"]').click()
    page.locator('#catalogVariantCodes').fill('04006381333931')
    page.locator('#catalogVariantBack').click()
    page.locator('#catalogVariantAdd').click()
    expect(page.locator('#catalogVariantForm .measurement-editor input')).to_have_value('900')
    expect(page.locator('#catalogVariantName')).to_have_value('Пакет 900 мл')
    page.locator('#catalogVariantForm button[type="submit"]').click()
    expect(page.locator('#catalogVariantSelect')).to_have_value('1')
    expect(page.locator('#catalogVariantCodes')).to_have_value('04006381333931')
    page.locator('[data-package-task="shops"]').click()
    page.locator('#catalogIdentityVariant').select_option('1')
    page.locator('#catalogIdentityCode').fill('000-42')
    expect(page.locator('#catalogIdentityUrl')).to_be_hidden()
    page.locator('.catalog-code-extra summary').click()
    page.locator('#catalogIdentityName').fill('МОЛОКО 900МЛ')
    page.locator('#catalogIdentityUrl').fill('https://example.com/item/42')
    page.evaluate("value => window.App.getRuntimeModule('catalog-identity').refresh(window.App.getRuntimeModule('catalog-products').normalizeProduct(value))", product)
    expect(page.locator('#catalogIdentityCode')).to_have_value('000-42')
    page.locator('#catalogOfferIdentityForm button[type="submit"]').click()
    expect(page.locator('#catalogIdentityStatus')).to_contain_text('Сохранено')
    page.locator('[data-product-tab="offers"]').click()
    page.locator('[data-product-tab="product"]').click()
    expect(page.locator('#catalogIdentityCode')).to_have_value('000-42')
    expect(page.locator('#catalogProductName')).to_have_value('Мой несохранённый товар')
    page.locator('[data-product-tab="packages"]').click()
    page.locator('[data-package-task="sizes"]').click()
    page.locator('[data-edit-variant="1"]').click()
    page.locator('#catalogVariantArchived').check()
    page.locator('#catalogVariantForm button[type="submit"]').click()
    expect(page.locator('#catalogVariantSelect option:checked')).to_contain_text('архив')
    page.locator('[data-edit-variant="1"]').click()
    for selector in ['#catalogVariantCodes','#catalogVariantName','#catalogVariantForm']:
        box=page.locator(selector).bounding_box()
        assert box['x']>=0 and box['x']+box['width']<=width+1
    page.locator('#catalogIdentityDetails').scroll_into_view_if_needed()
    page.screenshot(path=f'/tmp/fa-identity-{width}.png')
    assert writes[0][1]['codes']==['04006381333931']
    assert writes[1][1]['retailer_code']=='000-42' and writes[1][1]['variant_id']==1
    assert writes[-1][1]['is_archived'] is True
    assert errors==[]
