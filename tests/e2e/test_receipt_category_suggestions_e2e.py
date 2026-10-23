import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock
from tests.e2e.test_receipt_scan_e2e import start, stub, upload

TEXT='''ООО Соседи
№ ДОК 123
Опята маринованные Лорадо 314мл
7.89 x1.000 7.89
ИТОГО К ОПЛАТЕ 7.89
22.10.2026 20:33:06'''


def prepare(p, url, width):
    start(p,url,width)
    p.evaluate('''async()=>{
      await window.App.getRuntimeModule('operation-modal').receiptCatalog.load();
      window.App.state.categories.push({id:9801,name:'Консервы/соленья',icon:'🥫',kind:'expense'});
      window.App.state.receiptProductHints=[];
      window.App.state.receiptTemplateHints=[];
    }''')
    stub(p,TEXT);upload(p);p.click('#scanRun')
    return p.locator('.scan-row').first


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1440])
def test_proposed_category_survives_new_product_transfer_and_reopen(static_server_url,page_with_receipt_api_mock,width,tmp_path):
    p=page_with_receipt_api_mock;row=prepare(p,static_server_url,width)
    category=row.locator('[data-scan-category]')
    expect(category).to_have_value('9801')
    expect(row.locator('.scan-category')).to_contain_text('предложена')
    row.locator('[data-scan-field=name]').focus()
    row.locator('[data-receipt-create-name]').click()
    expect(category).to_have_value('9801')
    assert p.locator('#receiptScanDialog').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
    p.screenshot(path=str(tmp_path/f'category-{width}.png'))
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert item['category_id']==9801 and not item.get('product_id')
    assert float(item['unit_price'])==7.89 and float(item['quantity'])==1
    expect(p.locator('#opAmount')).to_have_value('7.89')
    p.click('#openReceiptScan');expect(p.locator('[data-scan-category]').first).to_have_value('9801')


@pytest.mark.e2e
@pytest.mark.parametrize('width',[390,1440])
def test_suggestion_changes_with_name_but_manual_clear_sticks(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;row=prepare(p,static_server_url,width)
    category=row.locator('[data-scan-category]');name=row.locator('[data-scan-field=name]')
    name.fill('Неизвестный продукт');name.press('Escape');expect(category).to_have_value('')
    name.fill('Опята маринованные');name.press('Escape');expect(category).to_have_value('9801')
    category.click();p.locator('#appChoiceDialog').get_by_role('button',name='Без категории',exact=True).click()
    name.fill('Огурчики маринованные');name.press('Escape');expect(category).to_have_value('')
    expect(row.locator('.scan-category')).not_to_contain_text('предложена')
    p.locator('#scanConfirmed').check();p.click('#scanTransfer')
    item=p.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert item['category_id'] is None and item['category_touched'] is True
    assert float(item['unit_price'])==7.89
