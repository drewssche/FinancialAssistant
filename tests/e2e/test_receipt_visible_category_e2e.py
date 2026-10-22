import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login, _ensure_categories_loaded


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1440])
@pytest.mark.parametrize('mode',['create','edit'])
def test_compact_category_visible_editable_and_no_money_change(static_server_url,page_with_receipt_api_mock,width,mode):
    p=page_with_receipt_api_mock;p.set_viewport_size({'width':width,'height':1100})
    p.goto(static_server_url+'/static/index.html');_login(p);_ensure_categories_loaded(p)
    if mode=='create':p.click('#addOperationCta')
    else:p.evaluate("window.App.actions.openEditModal({id:91,kind:'expense',amount:'12',operation_date:'2026-10-21',category_id:null,receipt_items:[]})")
    p.evaluate('''mode=>{
      const m=window.App.getRuntimeModule('operation-modal');
      window.App.state[mode+'ReceiptItems']=[
        m.createReceiptDraft({template_id:1,name:'Чебурек Марьино',quantity:2,unit_price:2.52,category_id:null},mode),
        m.createReceiptDraft({name:'Новый продукт',quantity:1,unit_price:3.79,category_id:101},mode),
      ];
      if(mode==='create')m.setCreateOperationMode('receipt');else m.setEditOperationMode('receipt');
      m.renderReceiptItems(mode);m.renderReceiptSummary(mode);
    }''',mode)
    root=p.locator('#'+mode+'Modal');rows=root.locator('.receipt-item-row');first=rows.nth(0);second=rows.nth(1)
    category=first.locator('[data-receipt-field=category_search]')
    expect(first.locator('[data-receipt-details-toggle]')).to_have_attribute('aria-expanded','false')
    expect(category).to_be_visible();expect(category).to_have_attribute('placeholder','Выбрать категорию')
    expect(first.locator('.is-missing-category')).to_be_visible()
    expect(second.locator('[data-receipt-field=category_search]')).to_be_visible()
    expect(second.locator('[data-receipt-field=category_search]')).to_have_value('Еда')
    category.click();first.locator('[data-receipt-category-id="101"]').click()
    expect(first.locator('[data-receipt-field=category_search]')).to_have_value('Еда')
    expect(first.locator('.is-missing-category')).to_have_count(0)
    expect(first.locator('[data-receipt-details-toggle]')).to_have_attribute('aria-expanded','false')
    assert p.evaluate("mode=>{const r=window.App.state[mode+'ReceiptItems'][0];return Number(r.category_id)===101&&Number(r.quantity)===2&&Number(r.unit_price)===2.52}",mode)
    assert root.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    p.screenshot(path=f'/tmp/fa-category-audit/{mode}-{width}.png')
