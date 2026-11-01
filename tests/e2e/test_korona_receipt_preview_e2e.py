import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url,page_with_receipt_api_mock
from tests.e2e.test_receipt_scan_e2e import start,stub,upload

TEXT='''Корона
№ ДОК 123
Блинчики с творогом
2276384 3.00 x2.000 6.00
Скидка -0.50
ИТОГО К ОПЛАТЕ 5.50
02.11.2026 12:30:00'''
ITEM={'name':'Блинчики Fattoria с творогом 500 г','url':'https://korona.by/our-production/syrniki-blinciki/blinciki-s-tvorogom',
      'source':'Корона','matched_by':'name','requires_confirmation':True,'price_unpublished':True,'site_price':None,
      'measurement':{'package_quantity':'500','package_unit':'g'},'size_label':'500 г','site_selection':'confirmed-korona-link',
      'image_token':None,'reference_only':False,'description':'Блинчики с творожной начинкой.'}

@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_name_match_requires_confirmation_and_preserves_receipt_money(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;calls=[];errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    p.route('**/api/v1/operations/catalog-products/lookup-codes',lambda r:r.fulfill(json={'items':[],'auto_match':False,'unmatched':['2276384']}))
    def site(route):
        calls.append(route.request.post_data_json);route.fulfill(json={'items':[ITEM],'auto_match':False,'state':'found','source':'Корона'})
    p.route('**/api/v1/operations/catalog-products/lookup-site-codes',site)
    start(p,static_server_url,width);stub(p,TEXT);upload(p);p.click('#scanRun')
    p.locator('#scanShop').fill('Корона')
    row=p.locator('.scan-row').first
    row.get_by_role('button',name='Найти на сайте по названию').click()
    expect(row.locator('.receipt-product-preview')).to_be_visible()
    expect(row).to_contain_text('Совпадение по названию · подтвердите товар')
    expect(row).to_contain_text('Сайт не публикует цену')
    assert calls[-1]['name']=='Блинчики с творогом' and calls[-1]['shop_name']=='Корона'
    assert calls[-1]['codes']==[{'kind':'retailer','code':'2276384'}]
    values=lambda:[row.locator('[data-scan-field='+key+']').input_value() for key in ['price','quantity','discount','total']]
    before=values();assert before==['3.00','2','0.50','5.50']
    # A lone name match must not apply even the optional package metadata.
    expect(row.get_by_role('spinbutton',name='Размер одной упаковки',exact=True)).to_have_count(0)
    row.get_by_role('button',name='Подтвердить товар и связать',exact=True).click()
    expect(row.get_by_role('button',name='Связь подтверждена')).to_be_disabled()
    assert values()==before
    assert p.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    p.screenshot(path=f'/tmp/fa-korona-preview-{width}.png')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert item['site_selection']=='confirmed-korona-link'
    assert float(item['unit_price'])*float(item['quantity'])==5.5
    assert float(item['discount_value'])==.5
    assert float(item['package_quantity'])==500 and item['package_unit']=='g'
    assert not errors


@pytest.mark.e2e
def test_search_without_code_and_no_match_does_not_block_transfer(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;calls=[]
    def site(route):
        calls.append(route.request.post_data_json);route.fulfill(json={'items':[],'auto_match':False,'state':'not_found','source':'Корона'})
    p.route('**/api/v1/operations/catalog-products/lookup-site-codes',site)
    start(p,static_server_url,390);stub(p,TEXT.replace('2276384 ',''));upload(p);p.click('#scanRun')
    p.locator('#scanShop').fill('Корона')
    row=p.locator('.scan-row').first
    row.get_by_role('button',name='Найти на сайте по названию').click()
    expect(row).to_contain_text('В каталоге Короны похожих товаров не найдено')
    assert calls[-1]['codes']==[]
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert item['site_selection'] is None and float(item['unit_price'])*float(item['quantity'])==5.5
