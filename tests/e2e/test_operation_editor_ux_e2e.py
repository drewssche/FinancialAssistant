"""Usability regressions: main controls must remain reachable, and detail folding must not change money."""
import pytest
from tests.e2e.test_receipt_picker_store_scope_e2e import (
    static_server_url, page_with_receipt_api_mock, _login, _ensure_categories_loaded,
)


def open_editor(page, url, width):
    page.set_viewport_size({'width': width, 'height': 844 if width < 900 else 900})
    page.goto(url + '/static/index.html')
    _login(page)
    _ensure_categories_loaded(page)
    page.click('#addOperationCta')
    page.wait_for_selector('#createModal:not(.hidden)')


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1024, 1100, 1440])
def test_simple_and_receipt_editors_keep_main_path_short(static_server_url, page_with_receipt_api_mock, width):
    page = page_with_receipt_api_mock
    open_editor(page, static_server_url, width)
    assert page.locator('#opAmount').is_visible()
    assert page.locator('#opNote').is_visible() == (width >= 900)
    assert page.locator('#opFxSettlementBlock').is_hidden()
    assert page.locator('#createModal .panel-head').bounding_box()['height'] < 90
    page.locator('#opAmount').fill('5.85')
    page.locator('#createOperationModeSwitch [data-operation-mode="receipt"]').click()
    assert page.locator('#opAmount').is_visible() == (width >= 900)
    page.locator('[data-receipt-store="create"]').fill('Соседи')
    page.locator('[data-receipt-store="create"]').press('Tab')
    page.locator('#receiptItemsList [data-receipt-field="name"]').first.fill('Сыр Голландский')
    page.locator('#createTitle').click()
    first = page.locator('#receiptItemsList .receipt-item-row').first
    first.locator('[data-receipt-field="quantity"]').fill('0.242')
    first.locator('[data-receipt-field="unit_price"]').fill('15.64')
    first.locator('[data-receipt-discount-toggle]').click()
    assert first.locator('[data-receipt-field="brand_search"]').is_hidden()
    assert first.locator('[data-receipt-field="regular_unit_price"]').is_visible()
    first.locator('[data-receipt-field="discount_value"]').fill('0.13')
    payload = page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert '3,65' in first.locator('.receipt-line-total strong').inner_text()
    assert payload[0]['shop_name'] == 'Соседи'
    first.locator('[data-receipt-field="discount_mode"]').select_option('final')
    first.locator('[data-receipt-field="discount_value"]').fill('3.50')
    first.locator('[data-receipt-field="quantity"]').fill('0.3')
    first.locator('[data-receipt-discount-toggle]').click()
    assert first.locator('.receipt-discount-calculation').is_hidden()
    payload = page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    assert float(payload[0]['discount_value']) == 3.5
    assert '3,50' in first.locator('.receipt-line-total strong').inner_text()
    first.locator('[data-receipt-details-toggle]').click()
    assert first.locator('[data-receipt-field="brand_search"]').is_visible()
    first.locator('[data-receipt-details-toggle]').click()
    assert page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()") == payload
    if width < 900:
        page.locator('#createModal .operation-receipt-check > summary').click()
    assert page.locator('#opAmount').input_value() == '5.85'
    page.locator('#pullReceiptTotalBtn').click()
    assert float(page.locator('#opAmount').input_value()) == 3.5
    page.locator('#createOperationModeSwitch [data-operation-mode="common"]').click()
    assert page.locator('#opAmount').is_visible()
    assert page.locator('#opCurrency').is_visible()
    page.locator('#createOperationModeSwitch [data-operation-mode="receipt"]').click()
    assert page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()") == payload
    assert page.locator('#createModal .modal-card').evaluate('n=>n.scrollWidth <= n.clientWidth + 1')


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1024, 1100, 1440])
def test_long_receipt_has_natural_height_and_preserves_saved_data(static_server_url, page_with_receipt_api_mock, width):
    page = page_with_receipt_api_mock
    open_editor(page, static_server_url, width)
    page.locator('#closeCreateModalBtn').click()
    page.evaluate('''async()=>{
      const items=Array.from({length:12},(_,i)=>({id:800+i,template_id:1,name:'Товар '+i,shop_name:'Соседи',quantity:1,unit_price:2.2,sale_unit:'piece',category_id:101}));
      await window.App.getRuntimeModule('operation-modal').openEditModal({id:777,kind:'expense',amount:'26.40',original_amount:'26.40',currency:'BYN',operation_date:'2026-10-13',receipt_items:items});
    }''')
    assert page.locator('[data-receipt-store="edit"]').input_value() == 'Соседи'
    first = page.locator('#editReceiptItemsList .receipt-item-row').first
    page.locator('#editModal .modal-card').evaluate('n=>n.scrollTop=0')
    assert first.bounding_box()['y'] < 380
    assert first.bounding_box()['height'] < (170 if width < 900 else 110)
    before = page.evaluate("() => window.App.getRuntimeModule('operation-modal').getEditReceiptPayload()")
    first.locator('[data-receipt-details-toggle]').click()
    first.locator('[data-receipt-details-toggle]').click()
    assert page.evaluate("() => window.App.getRuntimeModule('operation-modal').getEditReceiptPayload()") == before
    assert page.locator('#editReceiptDiffValue').is_hidden()
    assert not page.locator('#editReceiptDiffValue').evaluate("n=>n.classList.contains('receipt-diff-warn')")
    geometry = page.evaluate('''()=>{
      const fields=document.querySelector('#editReceiptFields').getBoundingClientRect();
      const rows=document.querySelector('#editReceiptItemsList').getBoundingClientRect();
      const extra=document.querySelector('#editModal .operation-extra').getBoundingClientRect();
      return {fieldsBottom:fields.bottom,rowsBottom:rows.bottom,extraTop:extra.top};
    }''')
    assert geometry['fieldsBottom'] >= geometry['rowsBottom']
    assert geometry['extraTop'] >= geometry['fieldsBottom'] - 1
    page.locator('#editReceiptTotalValue').scroll_into_view_if_needed()
    assert page.locator('#editModal .modal-card').evaluate('n=>n.scrollWidth <= n.clientWidth+1')
    page.screenshot(path=f'/tmp/fa-operation-long-{width}.png')


@pytest.mark.e2e
def test_store_inheritance_and_other_entry_modes_are_accessible(static_server_url, page_with_receipt_api_mock):
    page=page_with_receipt_api_mock
    open_editor(page,static_server_url,390)
    page.locator('#createOperationModeSwitch [data-operation-mode="receipt"]').click()
    store=page.locator('[data-receipt-store="create"]')
    store.fill('Соседи');store.press('Tab')
    rows=page.locator('#receiptItemsList .receipt-item-row')
    rows.nth(0).locator('[data-receipt-field="name"]').fill('Первый товар')
    page.locator('#createTitle').click()
    assert rows.nth(0).locator('[data-receipt-field="quantity"]').input_value() == '1'
    rows.nth(1).locator('[data-receipt-field="name"]').fill('Второй товар')
    page.locator('#createTitle').click()
    rows.nth(1).locator('[data-receipt-details-toggle]').click()
    rows.nth(1).locator('[data-receipt-field="shop_name"]').fill('Green')
    page.locator('#createTitle').click()
    store.fill('Евроопт');store.press('Tab')
    shops=page.evaluate('()=>window.App.state.createReceiptItems.map(x=>x.shop_name)')
    assert shops[:3] == ['Евроопт','Green','Евроопт']
    page.locator('#createModal .operation-entry > summary').click()
    page.locator('#createEntryModeSwitch [data-entry-mode="debt"]').click()
    assert page.locator('#debtPrincipal').is_visible()
    assert page.locator('#opReceiptBlock').is_hidden()
    page.locator('#createEntryModeSwitch [data-entry-mode="operation"]').click()
    assert page.locator('[data-receipt-store="create"]').is_visible()
    assert page.evaluate('()=>window.App.state.createReceiptItems.map(x=>x.shop_name)') == shops


@pytest.mark.e2e
@pytest.mark.parametrize('width', [390, 1440])
def test_compact_receipt_submits_exact_total_with_optional_comment(static_server_url, page_with_receipt_api_mock, width):
    import json
    page=page_with_receipt_api_mock
    captured=[]
    def save(route,request):
        if request.method != 'POST':
            route.fallback(); return
        payload=json.loads(request.post_data); captured.append(payload)
        route.fulfill(status=201,content_type='application/json',body=json.dumps({
            'id':778,**payload,'amount':'3.65','receipt_total':'3.65','receipt_discrepancy':'0.00',
        }))
    page.route('**/api/v1/operations',save)
    open_editor(page,static_server_url,width)
    page.locator('#createOperationModeSwitch [data-operation-mode="receipt"]').click()
    row=page.locator('#receiptItemsList .receipt-item-row').first
    row.locator('[data-receipt-field="name"]').fill('Сыр')
    page.locator('#createTitle').click()
    row.locator('[data-receipt-field="quantity"]').fill('0.242')
    row.locator('[data-receipt-field="unit_price"]').fill('15.64')
    row.locator('[data-receipt-discount-toggle]').click()
    row.locator('[data-receipt-field="discount_value"]').fill('0.13')
    if width < 900:
        page.locator('#createModal .operation-extra > summary').click()
    page.locator('#opNote').fill('Проверка черновика')
    page.locator('#submitCreateOperationBtn').click()
    page.wait_for_function("()=>document.querySelector('#createModal').classList.contains('hidden')")
    assert len(captured)==1
    assert captured[0]['amount'] is None
    assert captured[0]['note']=='Проверка черновика'
    item=captured[0]['receipt_items'][0]
    assert item['quantity']=='0.242'
    assert item['discount_mode']=='amount'
    assert float(item['discount_value'])==0.13
    assert float(item['regular_unit_price'])==15.64


@pytest.mark.e2e
def test_desktop_sidebar_resize_and_preview_preserve_draft(static_server_url, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
    open_editor(page, static_server_url, 1440)
    page.locator('#createOperationModeSwitch [data-operation-mode="receipt"]').click()
    page.evaluate('''()=>{
      const m=window.App.getRuntimeModule('operation-modal');
      window.App.state.createReceiptItems=[m.createReceiptDraft({template_id:1,name:'Сыр Голландский выдержанный',shop_name:'Соседи',sale_unit:'kg',quantity:.242,unit_price:15.64,category_id:101})];
      m.renderReceiptItems('create'); window.App.actions.updateCreatePreview();
    }''')
    page.locator('#opNote').fill('Семейные покупки')
    page.locator('#opAmount').fill('3.79')
    before = page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    for width in [390, 1024, 1100, 1440]:
        page.set_viewport_size({'width': width, 'height': 800})
        page.wait_for_timeout(100)
        assert page.locator('#opNote').count() == 1
        assert page.locator('#opNote').input_value() == 'Семейные покупки'
        assert page.locator('#opAmount').input_value() == '3.79'
        assert page.evaluate("() => window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()") == before
        assert page.locator('#createModal .modal-card').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
        if width >= 900:
            assert page.locator('#opNote').is_visible()
            assert page.locator('#opAmount').is_visible()
            assert page.locator('#createEntryModeSwitch').is_visible()
            geometry = page.evaluate('''()=>{
              const r=document.querySelector('#opReceiptBlock').getBoundingClientRect();
              const s=document.querySelector('#createModal .operation-summary-column').getBoundingClientRect();
              const h=document.querySelector('#createModal .panel-head').getBoundingClientRect();
              return {receiptRight:r.right,receiptTop:r.top,sidebarLeft:s.left,sidebarTop:s.top,headerHeight:h.height};
            }''')
            assert geometry['headerHeight'] < 90
            if width >= 1100:
                assert geometry['sidebarLeft'] >= geometry['receiptRight']
                assert abs(geometry['sidebarTop'] - geometry['receiptTop']) < 2
            page.screenshot(path=f'/tmp/fa-desktop-receipt-{width}.png')
    page.locator('#createModal .operation-preview-action').click()
    assert page.locator('#createPreviewBody').is_visible()
    page.locator('#createEntryModeSwitch [data-entry-mode="debt"]').click()
    assert page.locator('#debtPrincipal').is_visible()
    page.locator('#createEntryModeSwitch [data-entry-mode="operation"]').click()
    assert page.locator('#opNote').input_value() == 'Семейные покупки'
    assert page.locator('#opAmount').input_value() == '3.79'
    page.locator('#createOperationModeSwitch [data-operation-mode="common"]').click()
    assert page.locator('#opAmount').is_visible()
    assert page.locator('#opCurrency').is_visible()
    assert page.locator('#receiptTotalValue').is_hidden()


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1100, 1440])
def test_store_picker_and_header_follow_visual_contract(static_server_url, page_with_receipt_api_mock, width):
    page = page_with_receipt_api_mock
    open_editor(page, static_server_url, width)
    page.locator('#createOperationModeSwitch [data-operation-mode="receipt"]').click()
    store = page.locator('[data-receipt-store="create"]')
    assert store.get_attribute('list') is None
    store.click()
    popup = page.locator('#createReceiptStoreOptions')
    assert popup.is_visible()
    page.wait_for_timeout(50)
    box = popup.bounding_box()
    assert box['x'] >= 0 and box['x'] + box['width'] <= width
    assert box['height'] <= 281
    page.screenshot(path=f'/tmp/fa-consistent-store-{width}.png')
    popup.get_by_role('option', name='Соседи', exact=True).click()
    assert store.input_value() == 'Соседи'
    assert popup.is_hidden()
    assert page.evaluate('()=>window.App.state.createReceiptItems[0].shop_name') == 'Соседи'
    store.fill('Пкуут')  # Green entered with the wrong keyboard layout.
    assert popup.get_by_role('option', name='Green', exact=True).is_visible()
    store.press('ArrowDown')
    store.press('Enter')
    assert store.input_value() == 'Green'
    assert page.evaluate('()=>window.App.state.createReceiptItems[0].shop_name') == 'Green'
    store.click()
    store.press('Escape')
    assert popup.is_hidden()
    assert page.locator('#createModal').is_visible()
    store.click()
    last_name = popup.get_by_role('option').last.inner_text().replace('✓', '').strip()
    store.press('ArrowUp')
    store.press('Enter')
    assert store.input_value() == last_name
    store.fill('Новый магазин')
    popup.get_by_role('option', name='+ Новый магазин', exact=True).click()
    assert page.evaluate('()=>window.App.state.createReceiptItems[0].shop_name') == 'Новый магазин'
    store.click()
    store.press('Tab')
    assert popup.is_hidden()
    assert page.locator('#createModal .operation-tools').count() == 0
    preview = page.locator('#createModal .operation-preview-action')
    assert preview.is_visible()
    assert page.locator('#createSessionRefreshBtn').is_visible()
    preview.click()
    assert page.locator('#createPreviewBody').is_visible()
    preview.click()
    assert page.locator('#createPreviewBody').is_hidden()
    geometry = page.locator('#createOperationModeSwitch').evaluate('''n=>{
      const r=n.getBoundingClientRect(), buttons=[...n.querySelectorAll('button')].map(x=>x.getBoundingClientRect());
      return {left:buttons[0].left-r.left,right:r.right-buttons[1].right,widths:buttons.map(x=>x.width)};
    }''')
    assert geometry['left'] <= 6 and geometry['right'] <= 6
    assert abs(geometry['widths'][0] - geometry['widths'][1]) <= 1
    assert page.locator('#createModal .modal-card').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    store.click()
    page.locator('#closeCreateModalBtn').click()
    assert popup.is_hidden()
