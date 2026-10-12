from urllib.parse import urlparse
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login, _ensure_categories_loaded


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1440])
def test_receipt_comparison_lazy_exact_live_invalidated_and_retry(static_server_url, page_with_receipt_api_mock, width):
    page=page_with_receipt_api_mock
    page.set_viewport_size({'width':width,'height':1100})
    requests=[]; errors=[]; state={'fail':False,'hold':False,'pending':None}
    previous=dict(operation_id=120,receipt_item_id=250,recorded_at='2026-10-01',quantity='0.242',line_total='2.29',price=str(2.29/.242),is_discounted=True,discount_type='promo')
    page.on('pageerror',lambda error:errors.append(str(error)))
    def handler(route,req):
        path=urlparse(req.url).path
        if path.endswith('/401/price-hint'):
            requests.append(req.post_data_json)
            if state['hold']:
                state['pending']=route
                return
            return route.fulfill(status=503 if state['fail'] else 200,json={'detail':'Unavailable'} if state['fail'] else {'status':'found','previous':previous})
        if path.endswith('/catalog-products'):
            return route.fulfill(json={'items':[],'total':0,'page':1,'page_size':100})
        route.fallback()
    page.route('**/api/v1/operations/**',handler)
    page.goto(f'{static_server_url}/static/index.html')
    page.evaluate("window.Telegram={WebApp:{initData:'mock-init-data',ready(){},expand(){}}}")
    _login(page);_ensure_categories_loaded(page)
    page.click('#addOperationCta')
    page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
    page.evaluate('''() => {
      const modal=window.App.getRuntimeModule('operation-modal');
      window.App.state.createReceiptItems=[modal.createReceiptDraft({name:'Сыр',product_id:401,template_id:501,shop_name:'Магазин',sale_unit:'kg',quantity:.242,unit_price:10,is_discounted:true,regular_unit_price:10,discount_mode:'final',discount_value:2.39})];
      modal.renderReceiptItems('create');modal.renderReceiptSummary('create');
    }''')
    row=page.locator('#receiptItemsList .receipt-item-row').first
    hint=row.locator('.receipt-price-hint');button=hint.locator('button');label=hint.locator('small')
    expect(button).to_be_visible()
    assert requests==[]
    payload_before=page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    button.click()
    expect(label).to_contain_text('+4,37%')
    expect(label).to_contain_text('+0,1 BYN')
    assert requests[-1]['currency']=='BYN' and requests[-1]['sale_unit']=='kg'
    assert requests[-1]['exclude_operation_id'] is None
    assert page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()") == payload_before
    row.locator('[data-receipt-field="quantity"]').fill('0.484')
    expect(label).to_contain_text('-47,82%')
    expect(label).to_contain_text('-2,19 BYN')
    assert len(requests)==1
    box=hint.bounding_box();assert box['x']>=0 and box['x']+box['width']<=width+1
    page.screenshot(path=f'/tmp/fa-receipt-hints-{width}.png')
    # New currency/date invalidate the reference, without issuing more requests.
    page.evaluate("document.getElementById('opCurrency').value='USD';document.getElementById('opCurrency').dispatchEvent(new Event('change',{bubbles:true}))")
    expect(label).to_have_text('')
    assert len(requests)==1
    state['fail']=True;button.click();expect(label).to_contain_text('Можно повторить')
    state['fail']=False;button.click();expect(label).to_contain_text('USD')
    assert requests[-1]['currency']=='USD'
    state['hold']=True;button.click()
    expect(button).to_be_disabled()
    page.evaluate("document.getElementById('opCurrency').value='BYN';document.getElementById('opCurrency').dispatchEvent(new Event('change',{bubbles:true}))")
    expect(label).to_have_text('')
    state['pending'].fulfill(json={'status':'found','previous':previous})
    expect(label).to_have_text('')
    expect(button).to_be_enabled()
    state['hold']=False
    # Editing excludes the whole saved operation; no self-comparison.
    page.evaluate('''async () => {
      const modal=window.App.getRuntimeModule('operation-modal');window.App.actions.closeCreateModal();
      await modal.openEditModal({id:777,kind:'expense',amount:'3',original_amount:'3',currency:'BYN',operation_date:'2026-10-02',receipt_items:[{name:'Сыр',product_id:401,template_id:501,shop_name:'Магазин',quantity:1,unit_price:3,sale_unit:'kg'}]});
    }''')
    saved=page.locator('#editReceiptItemsList .receipt-item-row').first
    saved.locator('[data-receipt-price-hint]').click()
    expect(saved.locator('.receipt-price-hint small')).to_contain_text('01.10.2026')
    assert requests[-1]['exclude_operation_id']==777 and requests[-1]['as_of']=='2026-10-02'
    saved.locator('[data-receipt-details-toggle]').click()
    saved.locator('.receipt-measurements summary').click()
    saved.locator('[data-receipt-field="sale_unit"]').select_option('g')
    expect(saved.locator('.receipt-price-hint small')).to_have_text('')
    # Integer-ratio rounding, including a zero historical price.
    checks=page.evaluate('''() => {
      const compare=window.App.receiptPricing.compare;
      return [compare({quantity:3,unit_price:1},{quantity:3,line_total:'2.00'}),
              compare({quantity:1,unit_price:2},{quantity:1,line_total:'0.00'}),
              compare({quantity:0,unit_price:2},{quantity:1,line_total:'1.00'}),
              compare({quantity:1,unit_price:0},{quantity:1,line_total:'1.00'})];
    }''')
    assert checks[0]['percent']==50 and checks[0]['difference']==1
    assert checks[1]['percent'] is None and checks[1]['direction']==1
    assert checks[2] is None and checks[3] is None
    # The plan editor compares to actual purchases, using its own scheduled date.
    page.route('**/api/v1/plans/777',lambda route:route.fulfill(json={
        'id':777,'kind':'expense','status':'upcoming','amount':'3','currency':'BYN',
        'scheduled_date':'2026-10-15','recurrence_enabled':False,
        'receipt_items':[{'name':'Сыр','product_id':401,'template_id':501,'shop_name':'Магазин','quantity':1,'unit_price':3,'sale_unit':'kg'}]}))
    page.evaluate("document.getElementById('closeEditModalBtn').click()")
    page.evaluate("window.App.getRuntimeModule('plans').openPlanEdit(777)")
    expect(page.locator('#createTitle')).to_contain_text('Редактировать план')
    page.locator('#receiptItemsList [data-receipt-price-hint]').first.click()
    expect(page.locator('#receiptItemsList .receipt-price-hint small').first).to_contain_text('01.10.2026')
    assert requests[-1]['exclude_operation_id'] is None and requests[-1]['as_of']=='2026-10-15'
    assert errors==[]
