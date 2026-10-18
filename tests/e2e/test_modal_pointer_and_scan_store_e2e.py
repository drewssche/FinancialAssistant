import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login, _ensure_categories_loaded
from tests.e2e.test_receipt_scan_e2e import start, stub, upload


@pytest.mark.e2e
@pytest.mark.parametrize('mode', ['create', 'edit'])
def test_selecting_text_and_releasing_outside_keeps_operation(static_server_url, page_with_receipt_api_mock, mode):
    page = page_with_receipt_api_mock
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(static_server_url+'/static/index.html'); _login(page); _ensure_categories_loaded(page)
    if mode == 'create':
        page.click('#addOperationCta')
        field = page.locator('#opNote')
    else:
        page.evaluate("window.App.getRuntimeModule('operation-modal').openEditModal({id:77,kind:'expense',amount:'12.34',currency:'BYN',operation_date:'2026-10-16',note:'Текст'})")
        field = page.locator('#editNote')
    modal = page.locator('#'+mode+'Modal')
    field.fill('Не потерять изменения')
    box = field.bounding_box()
    page.mouse.move(box['x']+80,box['y']+box['height']/2)
    page.mouse.down(); page.mouse.move(5,5,steps=12); page.mouse.up()
    expect(modal).to_be_visible()
    expect(field).to_have_value('Не потерять изменения')
    # A deliberate click on the backdrop still closes the form.
    page.mouse.click(5,5)
    expect(modal).to_be_hidden()


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1440])
def test_scan_reuses_store_picker_in_dialog(static_server_url,page_with_receipt_api_mock,width):
    page=page_with_receipt_api_mock
    start(page,static_server_url,width); stub(page); upload(page); page.click('#scanRun')
    shop=page.locator('#scanShop'); popup=page.locator('#scanReceiptStoreOptions')
    page.locator('#scanConfirmed').check()
    shop.click()
    expect(popup).to_be_visible()
    assert popup.evaluate("n=>n.parentElement.id")=='receiptScanDialog'
    box=popup.bounding_box()
    assert 0 <= box['x'] and box['x']+box['width'] <= width
    page.screenshot(path=f'/tmp/fa-scan-store-{width}.png')
    popup.get_by_role('option',name='Евроопт',exact=True).click()
    expect(shop).to_have_value('Евроопт')
    expect(popup).to_be_hidden()
    expect(page.locator('#scanConfirmed')).not_to_be_checked()
    shop.click(); shop.press('Escape')
    expect(popup).to_be_hidden()
    expect(page.locator('#receiptScanDialog')).to_be_visible()
    shop.fill('Новый магазин'); popup.get_by_role('option',name='+ Новый магазин',exact=True).click()
    expect(shop).to_have_value('Новый магазин')
    page.locator('#scanConfirmed').check(); page.click('#scanTransfer')
    expect(page.locator('#receiptScanDialog')).to_be_hidden()
    assert page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload().every(r=>r.shop_name==='Новый магазин')")
    expect(popup).to_be_hidden()
