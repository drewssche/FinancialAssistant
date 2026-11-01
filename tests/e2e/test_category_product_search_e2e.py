import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _expand_receipt_row
from tests.e2e.test_receipt_scan_e2e import start, stub, upload
from tests.e2e.test_picker_creation_footers_e2e import check_footer


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_scan_product_category_search_create_and_transfer(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock; errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    start(p,static_server_url,width)
    p.evaluate("window.App.getRuntimeModule('operation-modal').receiptCatalog.load()")
    categories=[{'id':500+i,'kind':'expense','name':'Готовая еда '+str(i),'icon':'🍕'} for i in range(35)]
    categories.append({'id':600,'kind':'expense','name':'Перекус','icon':'🥪'})
    created={'id':700,'name':'Суши','kind':'expense','icon':None,'group_id':None}
    def cats(route):
        if route.request.method=='POST':
            assert route.request.post_data_json['name']=='Суши'
            categories.append(created);route.fulfill(status=201,json=created)
        else:
            route.fulfill(json={'items':categories,'total':len(categories),'page':1,'page_size':500} if '?' in route.request.url else categories)
    p.route('**/api/v1/categories',cats);p.route('**/api/v1/categories?*',cats)
    p.evaluate("cats=>{window.App.state.categories=cats;window.App.state.receiptProductHints=[{id:1,name:'Пицца Маргарита',category_id:500},{id:2,name:'Пицца овощная',category_id:600},{id:3,name:'Пицца архивная',category_id:501,is_archived:true}];}",categories)
    stub(p);upload(p);p.click('#scanRun')
    row=p.locator('.scan-row').first;field=row.locator('.scan-category input');picker=p.locator('#'+field.get_attribute('aria-controls'))
    field.fill('пицца');expect(picker.get_by_role('option')).to_have_count(4) # none, two categories, create
    expect(picker).to_contain_text('Есть товары: Пицца Маргарита');expect(picker).to_contain_text('Перекус')
    assert 'Пицца архивная' not in picker.inner_text()
    p.screenshot(path=f'/tmp/fa-scan-category-search-{width}.png')
    picker.get_by_role('option').filter(has_text='Маргарита').click()
    expect(row.locator('[data-scan-category]')).to_have_value('500')
    field.fill('Готовая');check_footer(p,picker,width)
    field.fill('Суши');picker.locator('.chip-btn-create').click()
    modal=p.locator('#createCategoryModal');expect(modal).to_be_visible()
    assert modal.evaluate("n=>n.closest('dialog').id==='receiptScanDialog'")
    expect(p.locator('#categoryName')).to_have_value('Суши')
    p.keyboard.press('Escape');expect(modal).to_be_hidden();expect(p.locator('#receiptScanDialog')).to_be_visible()
    field.fill('Суши');field.press('ArrowUp');field.press('Enter');expect(modal).to_be_visible()
    p.screenshot(path=f'/tmp/fa-scan-create-category-{width}.png')
    modal.locator('button[type=submit]').click()
    expect(modal).to_be_hidden();expect(field).to_have_value('Суши');expect(row.locator('[data-scan-category]')).to_have_value('700')
    assert modal.evaluate("n=>!n.closest('dialog')")
    other=p.locator('.scan-row').nth(1);other_field=other.locator('.scan-category input');other_field.fill('Суши')
    p.locator('#'+other_field.get_attribute('aria-controls')).get_by_role('option',name='Суши',exact=True).click()
    expect(other.locator('[data-scan-category]')).to_have_value('700')
    field.click();p.keyboard.press('Escape');expect(picker).to_be_hidden();expect(p.locator('#receiptScanDialog')).to_be_visible()
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    payload=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert payload[0]['category_id']==700 and float(payload[0]['quantity'])==2 and float(payload[0]['unit_price'])*float(payload[0]['quantity'])==5.5
    assert not errors


@pytest.mark.e2e
def test_operation_category_search_uses_catalogue(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;start(p,static_server_url);p.click('#scanClose')
    p.evaluate("async()=>{await window.App.getRuntimeModule('operation-modal').receiptCatalog.load();window.App.state.receiptProductHints=[{id:987,name:'Пицца тестовая',category_id:101}];}")
    row=p.locator('.receipt-item-row').first
    row.locator('[data-receipt-field=name]').fill('Новая пицца')
    p.locator('[data-receipt-create-name="Новая пицца"]').click()
    _expand_receipt_row(row)
    field=p.locator('.receipt-item-row').first.locator('[data-receipt-field=category_search]');field.fill('пицца')
    picker=p.locator('.receipt-category-picker').first
    expect(picker).to_contain_text('Есть товары: Пицца тестовая')
    picker.locator('[data-receipt-category-id="101"]').click()
    expect(field).to_have_value('Еда')


@pytest.mark.e2e
def test_korona_source_link_in_catalogue_and_scan(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock
    source={'id':20,'name':'Корона','is_archived':False,'website_url':'https://korona.by/our-production'}
    p.route('**/api/v1/operations/item-sources*',lambda r:r.fulfill(json={'items':[source],'total':1,'page':1,'page_size':500}))
    p.route('**/api/v1/operations/catalog-products/lookup-site-codes',lambda r:r.fulfill(json={'items':[],'auto_match':False,'state':'unsupported'}))
    start(p,static_server_url,390)
    p.evaluate("window.App.getRuntimeModule('operation-modal').receiptCatalog.load()")
    stub(p);upload(p);p.click('#scanRun')
    p.locator('#scanShop').fill('Корона');p.locator('#scanShop').press('Tab')
    row=p.locator('.scan-row').first
    row.get_by_role('button',name='Найти по коду',exact=True).click()
    expect(row.get_by_role('link',name='Каталог источника')).to_have_attribute('href',source['website_url'])
    p.click('#scanClose')
    p.evaluate("window.App.getRuntimeModule('item-catalog').openEditSourceGroupModal('Корона')")
    expect(p.locator('#sourceGroupModal').get_by_role('link',name='Каталог продукции')).to_have_attribute('href',source['website_url'])
