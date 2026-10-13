import json
from urllib.parse import urlparse, parse_qs
from decimal import Decimal

import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login, _ensure_categories_loaded


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1440])
def test_product_workspace_and_compact_receipt_preserve_drafts(static_server_url, page_with_receipt_api_mock, width):
    page = page_with_receipt_api_mock
    page.set_viewport_size({'width': width, 'height': 1100})
    errors, requests, deleted = [], [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    product = {'id': 401, 'name': 'Крупа длинное название 900 г', 'brand_name': 'Бренд', 'category_id': 101,
               'sale_unit': 'pack', 'package_quantity': '900', 'package_unit': 'g',
               'offers': [{'id': 501, 'source_id': 301, 'source_name': 'Green', 'name': 'Крупа магазин А', 'latest_unit_price': '4'},
                          {'id': 502, 'source_id': 302, 'source_name': 'Соседи', 'name': 'Крупа магазин Б', 'latest_unit_price': '5'}]}
    def handler(route, req):
        parsed = urlparse(req.url); path = parsed.path; query = parse_qs(parsed.query)
        if '/catalog-products' in path:
            if path.endswith('merge-candidates'): payload = {'items': [], 'total': 0}
            elif path.endswith('/401'): payload = product
            else: payload = {'items': [product], 'total': 1, 'page': 1, 'page_size': 100}
        elif path == '/api/v1/operations/51':
            payload = {'id': 51, 'kind': 'expense', 'amount': '8', 'original_amount': '8', 'currency': 'BYN', 'operation_date': '2026-10-12', 'receipt_items': []}
        elif '/prices' in path:
            requests.append(path)
            if req.method == 'DELETE': deleted.append(path); payload = {'id': 501, 'product_id': 401}
            else: payload = [] if deleted else [{'id': 99, 'recorded_at': '2026-10-12', 'unit_price': '4'}]
        elif path.endswith('/money-flow') and 'product_id' in query:
            requests.append(query)
            start = (int(query['page'][0])-1)*50
            payload = {'total': 51, 'items': [{'source_kind': 'operation', 'source_id': i+1, 'event_date': '2026-10-12',
                'amount': '8', 'currency': 'BYN', 'receipt_items': [{'product_id': 401, 'shop_name': 'Green'}]} for i in range(start,min(start+50,51))]}
        else: return route.fallback()
        route.fulfill(json=payload)
    page.route('**/api/v1/operations/**', handler)
    page.goto(f'{static_server_url}/static/index.html')
    page.evaluate("window.Telegram = {WebApp: {initData: 'mock-init-data', ready() {}, expand() {}}}")
    _login(page); _ensure_categories_loaded(page)
    page.click('#addOperationCta')
    page.locator('#createOperationModeSwitch [data-operation-mode="receipt"]').click()
    row = page.locator('#receiptItemsList .receipt-item-row').first
    row.locator('[data-receipt-field="name"]').fill('Крупа')
    page.locator('[data-receipt-product-id="401"]').first.click()
    expect(row).to_have_class(__import__('re').compile('is-compact'))
    expect(row.locator('[data-receipt-field="name"]')).to_be_hidden()
    expect(row.locator('.receipt-compact-heading')).to_contain_text('900 г')
    row.locator('[data-receipt-field="quantity"]').fill('2')
    row.locator('[data-receipt-field="unit_price"]').fill('4')
    expect(row.locator('.receipt-line-total')).to_contain_text('8,00')
    before = page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    page.screenshot(path=f'/tmp/fa-compact-receipt-{width}.png', full_page=False)
    for target in [row, row.locator('.receipt-item-money')]:
        box = target.bounding_box()
        assert box['x'] >= 0 and box['x']+box['width'] <= width+1
    row.locator('.receipt-compact-name').click()
    modal = page.locator('#catalogProductModal')
    expect(modal).to_be_visible()
    page.locator('#catalogProductName').fill('Несохранённый черновик')
    page.locator('[data-product-tab="offers"]').click()
    expect(page.locator('#catalogProductOffersList')).to_contain_text('Соседи')
    page.locator('[data-modal-offer-id="502"] [data-product-offer-action="history"]').click()
    expect(page.locator('#catalogProductPriceOffer')).to_have_value('502')
    page.locator('#catalogProductPriceMode').select_option('offers')
    expect(page.locator('#catalogProductPricesList')).to_contain_text('4,00')
    page.screenshot(path=f'/tmp/fa-product-prices-{width}.png', full_page=False)
    page.locator('[data-product-tab="purchases"]').click()
    expect(page.locator('[data-product-purchase-id]')).to_have_count(50)
    page.locator('#catalogProductMorePurchases').click()
    expect(page.locator('[data-product-purchase-id]')).to_have_count(51)
    assert all('date_from' not in q and 'q' not in q for q in requests if isinstance(q,dict))
    page.locator('[data-product-purchase-id="51"]').click()
    expect(page.locator('#editModal')).to_be_visible()
    page.locator('#closeEditModalBtn').click()
    expect(page.locator('[data-product-purchase-id="51"]')).to_be_focused()
    expect(page.locator('[data-product-purchase-id]')).to_have_count(51)
    page.locator('[data-product-tab="prices"]').click()
    page.locator('#catalogProductPriceMode').select_option('offers')
    page.locator('[data-product-price-delete]').click()
    # Cancel keeps the record and parent draft intact.
    page.locator('#confirmCancelBtn').click()
    assert deleted == []

    page.locator('[data-product-tab="product"]').click()
    expect(page.locator('#catalogProductName')).to_have_value('Несохранённый черновик')
    page.keyboard.press('Escape')
    expect(modal).to_be_hidden()
    expect(row.locator('.receipt-compact-name')).to_be_focused()
    assert page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()") == before
    row.locator('[data-receipt-details-toggle]').click()
    expect(row.locator('[data-receipt-field="name"]')).to_be_visible()
    row.locator('.receipt-measurements summary').click()
    row.locator('[data-receipt-field="package_quantity"]').fill('800')
    row.locator('[data-receipt-details-toggle]').click()
    expect(row.locator('.receipt-compact-heading')).to_contain_text('800 г')
    # The inline discount action expands settings; money stays accessible.
    row.locator('[data-receipt-discount-toggle]').click()
    row.locator('[data-receipt-field="discount_mode"]').select_option('final')
    row.locator('[data-receipt-field="discount_value"]').fill('7.65')
    page.screenshot(path=f'/tmp/fa-expanded-receipt-{width}.png', full_page=False)
    geometry = row.evaluate('node => ({width: node.clientWidth, content: node.scrollWidth})')
    assert geometry['content'] <= geometry['width'] + 1
    row.locator('[data-receipt-details-toggle]').click()
    expect(row.locator('.receipt-line-total')).to_contain_text('7,65')
    row.locator('[data-receipt-field="quantity"]').fill('3')
    expect(row.locator('.receipt-line-total')).to_contain_text('7,65')
    result = page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert Decimal(result['discount_value']) == Decimal('7.65')
    assert result['package_quantity'] == '800'
    assert errors == []


@pytest.mark.e2e
def test_offer_detach_price_delete_and_bulk_merge_stay_available(static_server_url, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
    page.set_viewport_size({'width': 390, 'height': 1000})
    calls, errors = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    product = {'id': 401, 'name': 'Товар А', 'category_id': 101, 'offers': [
        {'id': 501, 'product_id': 401, 'name': 'Предложение А', 'source_name': 'Green', 'latest_unit_price': '3'},
        {'id': 502, 'product_id': 401, 'name': 'Предложение Б', 'source_name': 'Соседи', 'latest_unit_price': '4'}]}
    products = [product]
    def handler(route, req):
        path = urlparse(req.url).path
        if req.method not in ('GET', 'HEAD'): calls.append((req.method, path))
        if path.endswith('/501/detach'):
            products.append({'id': 402, 'name': 'Предложение А', 'offers': [product['offers'].pop(0)]})
            payload = products[-1]
        elif '/prices/' in path:
            payload = {'id': 502, 'product_id': 401}
        elif path.endswith('/prices'):
            payload = [] if any(m == 'DELETE' for m,p in calls) else [{'id': 99, 'recorded_at': '2026-10-12', 'unit_price': '4'}]
        elif path.endswith('merge-candidates'): payload = {'items': [], 'total': 0}
        elif path.endswith('/catalog-products/401'): payload = product
        elif path.endswith('/catalog-products'): payload = {'items': products, 'total': len(products), 'page': 1, 'page_size': 100}
        elif path.endswith('/item-templates/501'): payload = product['offers'][0]
        else: return route.fallback()
        route.fulfill(json=payload)
    page.route('**/api/v1/operations/**', handler)
    page.goto(f'{static_server_url}/static/index.html')
    page.evaluate("window.Telegram = {WebApp: {initData: 'mock-init-data', ready() {}, expand() {}}}")
    _login(page)
    # A linked source/legacy receipt entry opens the same product workspace.
    page.evaluate("window.App.getRuntimeModule('catalog-media').openItemTemplateCard(501)")
    expect(page.locator('[data-product-tab="offers"]')).to_have_attribute('aria-pressed', 'true')
    page.locator('[data-product-tab="product"]').click()
    page.locator('#catalogProductName').fill('Черновик названия')
    page.locator('[data-product-tab="offers"]').click()
    page.locator('[data-modal-offer-id="501"] [data-product-offer-action="edit"]').click()
    expect(page.locator('#itemTemplateModal')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('[data-modal-offer-id="501"] [data-product-offer-action="edit"]')).to_be_focused()
    page.locator('[data-modal-offer-id="501"] [data-product-offer-action="detach"]').click()
    page.locator('#confirmCancelBtn').click()
    assert calls == []
    page.locator('[data-modal-offer-id="501"] [data-product-offer-action="detach"]').click()
    page.locator('#confirmDeleteBtn').click()
    expect(page.locator('[data-modal-offer-id="501"]')).to_have_count(0)
    expect(page.locator('[data-modal-offer-id="502"]')).to_be_visible()
    assert ('POST', '/api/v1/operations/catalog-products/401/offers/501/detach') in calls
    page.locator('[data-product-tab="prices"]').click()
    page.locator('#catalogProductPriceMode').select_option('offers')
    page.locator('[data-product-price-delete]').click()
    page.locator('#confirmDeleteBtn').click()
    expect(page.locator('#catalogProductPricesList')).to_contain_text('пустая')
    assert ('DELETE', '/api/v1/operations/item-templates/502/prices/99') in calls
    page.locator('[data-product-tab="product"]').click()
    expect(page.locator('#catalogProductName')).to_have_value('Черновик названия')
    page.locator('#closeCatalogProductModalBtn').click()
    page.evaluate("window.App.getRuntimeModule('navigation').switchSection('item_catalog')")
    for id in (401,402): page.locator(f'[data-select-catalog-product-id="{id}"]').check()
    page.locator('#mergeCatalogProductsBtn').click()
    expect(page.locator('#catalogProductMergeModal')).to_be_visible()
    expect(page.locator('#catalogProductMergeOptions input')).to_have_count(2)
    page.keyboard.press('Escape')
    assert errors == []


@pytest.mark.e2e
def test_late_price_response_and_nested_purchase_cannot_replace_draft(static_server_url, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
    errors=[]
    page.on('pageerror', lambda error: errors.append(str(error)))
    product={'id':401,'name':'Товар','offers':[{'id':501,'name':'А','source_name':'Green'}, {'id':502,'name':'Б','source_name':'Соседи'}]}
    page.route('**/api/v1/operations/catalog-products/401', lambda route: route.fulfill(json=product))
    page.route('**/api/v1/operations/money-flow?**', lambda route: route.fulfill(json={'total':1,'items':[{'source_id':123,'source_kind':'operation','event_date':'2026-10-12','amount':'8','currency':'BYN'}]}))
    page.goto(f'{static_server_url}/static/index.html')
    page.evaluate("window.Telegram = {WebApp: {initData: 'mock-init-data', ready() {}, expand() {}}}")
    _login(page)
    page.evaluate('''async () => {
      await window.App.getRuntimeModule('operation-modal').openEditModal({id:777,kind:'expense',amount:'8',original_amount:'8',currency:'BYN',operation_date:'2026-10-12',receipt_items:[{product_id:401,template_id:501,name:'Товар',quantity:'2',unit_price:'4',sale_unit:'pack'}]});
      const original = window.App.core.requestJson;
      window.App.core.requestJson = (url, options) => {
        if(url.includes('/501/prices')) return new Promise(resolve => {window.releaseOldPrice = resolve});
        if(url.includes('/502/prices')) return Promise.resolve([{id:2,recorded_at:'2026-10-12',unit_price:'22'}]);
        return original(url, options);
      };
    }''')
    before=page.evaluate("window.App.getRuntimeModule('operation-modal').getEditReceiptPayload()")
    page.locator('#editReceiptItemsList .receipt-compact-name').click()
    page.locator('[data-product-tab="prices"]').click()
    page.locator('#catalogProductPriceMode').select_option('offers')
    page.wait_for_function("typeof window.releaseOldPrice === 'function'")
    page.locator('#catalogProductPriceOffer').select_option('502')
    expect(page.locator('#catalogProductPricesList')).to_contain_text('22,00')
    page.evaluate("window.releaseOldPrice([{id:1,recorded_at:'2026-10-12',unit_price:'99'}])")
    expect(page.locator('#catalogProductPricesList')).not_to_contain_text('99,00')
    page.locator('[data-product-tab="purchases"]').click()
    page.locator('[data-product-purchase-id="123"]').click()
    expect(page.locator('#catalogProductModal')).to_be_visible()
    assert page.evaluate("window.App.getRuntimeModule('operation-modal').getEditReceiptPayload()") == before
    page.keyboard.press('Escape')
    expect(page.locator('#editModal')).to_be_visible()
    expect(page.locator('#editReceiptItemsList .receipt-compact-name')).to_be_focused()
    assert errors == []
