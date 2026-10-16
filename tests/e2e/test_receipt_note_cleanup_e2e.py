import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url,page_with_receipt_api_mock,_login


@pytest.mark.e2e
def test_legacy_ocr_hidden_but_user_comment_preserved(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;p.goto(f'{static_server_url}/static/index.html')
    p.evaluate("window.Telegram={WebApp:{initData:'mock-init-data',ready(){},expand(){}}}");_login(p)
    p.evaluate('''()=>window.App.actions.openOperationReceiptModal({id:77,amount:'10.39',currency:'BYN',operation_date:'2026-10-15',receipt_items:[
      {name:'Пельмени',quantity:1,unit_price:5.99,note:'OCR: 2186323 Пельмени 430 г 5.99 x1.000 5.99'},
      {name:'Сырок',quantity:4,unit_price:1.10,note:'Для завтрака'}]})''')
    expect(p.locator('#operationReceiptModal')).to_be_visible()
    expect(p.locator('#operationReceiptItems')).not_to_contain_text('OCR:')
    expect(p.locator('#operationReceiptItems')).to_contain_text('Для завтрака')
    p.locator('#operationReceiptModal').screenshot(path='/tmp/fa-receipt-clean-notes.png')
