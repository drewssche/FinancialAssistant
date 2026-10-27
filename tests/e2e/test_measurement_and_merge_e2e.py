import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login, _ensure_categories_loaded
from tests.e2e.test_receipt_scan_e2e import start, stub, upload


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1440])
def test_same_package_editor_in_scan_operation_and_catalog(static_server_url,page_with_receipt_api_mock,width):
    page=page_with_receipt_api_mock
    start(page,static_server_url,width);stub(page);upload(page);page.click('#scanRun')
    row=page.locator('#scanRows .scan-row').first
    editor=row.locator('.measurement-editor')
    editor.locator('[data-scan-unit=pack]').click()
    editor.get_by_role('spinbutton').fill('250')
    editor.locator('[data-unit=g]').click()
    expect(row.locator('[data-scan-field=quantity]')).to_have_value('2')
    expect(row.locator('[data-scan-field=total]')).to_have_value('5.50')
    page.locator('#scanConfirmed').check();page.click('#scanTransfer')
    payload=page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert payload['sale_unit']=='pack' and payload['package_quantity']=='250' and payload['package_unit']=='g'
    page.evaluate("window.App.state.createReceiptItems[0].details_expanded=true;window.App.getRuntimeModule('operation-modal').renderReceiptItems('create')")
    operation=page.locator('#receiptItemsList .measurement-editor').first
    expect(operation.locator('[data-sale-unit=pack]')).to_have_attribute('aria-pressed','true')
    expect(operation.get_by_role('spinbutton')).to_have_value('250')
    operation.locator('[data-sale-unit=piece]').click()
    payload=page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert payload['sale_unit']=='piece' and payload['package_quantity']=='250' and payload['quantity']=='2'
    page.evaluate("window.App.getRuntimeModule('operation-modal').closeCreateModal();window.App.getRuntimeModule('catalog-products').openEditor()")
    editor=page.locator('#catalogProductModal .measurement-editor')
    expect(editor.locator('[data-sale-unit=""]')).to_have_attribute('aria-pressed','true')
    editor.locator('[data-sale-unit=pack]').click();editor.get_by_role('spinbutton').fill('250');editor.locator('[data-unit=g]').click()
    expect(page.locator('#catalogProductSaleUnit')).to_have_value('pack')
    expect(page.locator('#catalogProductPackageQuantity')).to_have_value('250')
    expect(page.locator('#catalogProductPackageUnit')).to_have_value('g')
    assert editor.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    page.screenshot(path=f'/tmp/fa-measurement-editor-{width}.png')
    editor.locator('[data-sale-unit=kg]').click()
    expect(editor.get_by_role('spinbutton')).to_be_hidden()
    expect(page.locator('#catalogProductPackageQuantity')).to_have_value('')
    expect(page.locator('#catalogProductPackageUnit')).to_have_value('')


@pytest.mark.e2e
def test_merge_error_is_visible_and_retry_submits_selected_target(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock
    page.goto(static_server_url+'/static/index.html');_login(page);_ensure_categories_loaded(page)
    requests=[]
    def merge(route):
        requests.append(route.request.post_data_json)
        route.fulfill(status=400 if len(requests)==1 else 200,json={'detail':'Размеры упаковки различаются'} if len(requests)==1 else {'source_conflicts':[]})
    page.route('**/catalog-products/401/merge',merge)
    page.evaluate("""() => window.App.getRuntimeModule('catalog-products').openMerge([
        {id:401,name:'Зефир 250г',sale_unit:'pack',package_quantity:'1',package_unit:'piece',offers_count:1,sources_count:1,offers:[]},
        {id:402,name:'Зефир 250г',sale_unit:'piece',package_quantity:'1',package_unit:'piece',offers_count:1,sources_count:1,offers:[]}
    ])""")
    expect(page.locator('#catalogProductMergeOptions')).to_contain_text('упак.')
    page.click('#submitCatalogProductMergeBtn')
    expect(page.locator('#catalogProductMergeError')).to_have_text('Размеры упаковки различаются')
    expect(page.locator('#catalogProductMergeModal')).to_be_visible()
    expect(page.locator('#submitCatalogProductMergeBtn')).to_be_enabled()
    page.click('#submitCatalogProductMergeBtn')
    expect(page.locator('#catalogProductMergeModal')).to_be_hidden()
    assert requests==[{'source_product_ids':[402]},{'source_product_ids':[402]}]


@pytest.mark.e2e
def test_merge_weighted_product_label_does_not_repeat_unit(static_server_url, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
    page.goto(static_server_url + '/static/index.html')
    _login(page)
    _ensure_categories_loaded(page)
    page.evaluate("""() => window.App.getRuntimeModule('catalog-products').openMerge([
        {id:568,name:'Рулет Столичный 1кг',sale_unit:'kg',offers_count:1,sources_count:1,offers:[{id:598,source_name:'Маяк',latest_unit_price:'18.59'}]},
        {id:519,name:'Рулет Столичный 1кг',sale_unit:null,offers_count:1,sources_count:1,offers:[{id:542,source_name:'Green',latest_unit_price:'19.39'}]}
    ])""")
    options = page.locator('#catalogProductMergeOptions')
    expect(options).to_contain_text('Маяк')
    expect(options).to_contain_text('Green')
    expect(options).to_contain_text('1 предл. · 1 источн. · кг')
    expect(options).not_to_contain_text('кг · кг')
    expect(options).to_contain_text('Единица не указана')
