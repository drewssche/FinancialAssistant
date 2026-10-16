"""Interaction contracts: searchable choices, explicit units and unchanged historical data."""
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login, _ensure_categories_loaded


def start(page, url, width):
    page.set_viewport_size({'width': width, 'height': 1000})
    page.goto(url + '/static/index.html')
    _login(page); _ensure_categories_loaded(page)
    page.click('#addOperationCta')
    expect(page.locator('#createModal')).to_be_visible()


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1440])
def test_searchable_choice_keyboard_escape_and_preview(static_server_url, page_with_receipt_api_mock, width):
    page = page_with_receipt_api_mock
    errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
    start(page, static_server_url, width)
    select = page.locator('#opCurrency')
    original = select.input_value()
    select.click()
    dialog = page.locator('#appChoiceDialog')
    expect(dialog).to_be_visible()
    search = dialog.get_by_role('searchbox')
    expect(search).to_be_focused()
    search.fill('no-such-currency')
    expect(dialog.locator('[role=status]')).to_have_text('Ничего не найдено')
    search.press('Escape')
    expect(dialog).not_to_be_visible()
    expect(page.locator('#createModal')).to_be_visible()
    expect(select).to_have_value(original)
    expect(select).to_be_focused()
    select.press('ArrowDown')
    search.fill('USD'); search.press('Enter')
    expect(select).to_have_value('USD')
    expect(dialog).not_to_be_visible()
    # Wrong keyboard layout also works in all select-backed pickers.
    page.evaluate("document.querySelector('#opCurrency').add(new Option('Российский рубль','RUB'))")
    select.click(); search.fill('hjccbqcrbq')
    expect(dialog.locator('.choice-option')).to_have_count(1)
    dialog.locator('.choice-option').click()
    expect(select).to_have_value('RUB')
    preview = page.locator('#createModal .operation-preview-action')
    expect(preview).to_have_attribute('aria-pressed', 'false')
    preview.click(); expect(preview).to_have_attribute('aria-pressed', 'true')
    expect(preview).to_have_class(__import__('re').compile('is-active'))
    page.screenshot(path=f'/tmp/fa-simple-preview-{width}.png')
    preview.click(); expect(preview).to_have_attribute('aria-pressed', 'false')
    select.select_option(original)
    settings = page.locator('#createModal button[aria-label="Валютный остаток"]')
    settings.click()
    task = page.locator('#createModal .task-dialog')
    expect(task).to_be_visible()
    expect(page.locator('#opUseFxSettlement')).to_be_attached()
    task.get_by_role('button', name='Закрыть настройки').press('Escape')
    expect(task).not_to_be_visible()
    expect(page.locator('#createModal')).to_be_visible()
    expect(settings).to_be_focused()
    select.click()
    page.evaluate("window.App.actions.closeCreateModal()")
    expect(dialog).not_to_be_visible()
    expect(page.locator('#createModal')).not_to_be_visible()
    assert errors == []


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1440])
def test_milk_litre_weight_and_untouched_snapshot(static_server_url, page_with_receipt_api_mock, width):
    page = page_with_receipt_api_mock
    start(page, static_server_url, width)
    page.locator('#createOperationModeSwitch [data-operation-mode="receipt"]').click()
    page.evaluate('''() => {
      const m=window.App.getRuntimeModule('operation-modal');
      window.App.state.createReceiptItems=[m.createReceiptDraft({name:'Молоко',quantity:2,unit_price:3,details_expanded:true})];
      m.renderReceiptItems('create');
    }''')
    row = page.locator('#receiptItemsList .receipt-item-row').first
    size = row.locator('.measurement-editor')
    size.get_by_role('spinbutton').fill('1')
    size.locator('[data-unit=l]').click()
    payload = page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert payload['sale_unit'] == 'piece' and payload['package_unit'] == 'l'
    assert payload['package_quantity'] == '1' and payload['quantity'] == '2' and float(payload['unit_price']) == 3
    page.screenshot(path=f'/tmp/fa-simple-milk-{width}.png')
    size.locator('[data-measure-kind=weight]').click()
    row.locator('[data-receipt-field=quantity]').fill('0.242')
    payload = page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert payload['sale_unit'] == 'kg' and payload['package_quantity'] is None and payload['package_unit'] is None
    assert payload['quantity'] == '0.242'
    assert row.locator('.measurement-editor').evaluate('n=>n.scrollWidth<=n.clientWidth+1')


@pytest.mark.e2e
def test_import_help_closes_independently_and_with_owner(static_server_url, page_with_receipt_api_mock):
    page=page_with_receipt_api_mock
    start(page,static_server_url,390)
    page.evaluate("window.App.actions.closeCreateModal();window.App.getRuntimeModule('bulk-ui').openBatchCreateModal()")
    owner=page.locator('#batchCreateModal');trigger=page.locator('#batchCreateHint')
    trigger.click()
    help=page.get_by_role('dialog',name='Формат импорта',exact=True)
    expect(help).to_be_visible();expect(help).to_contain_text('Дата: ДД.ММ.ГГГГ')
    page.keyboard.press('Escape')
    expect(help).to_be_hidden();expect(owner).to_be_visible();expect(trigger).to_be_focused()
    trigger.click()
    page.evaluate("window.App.getRuntimeModule('bulk-ui').closeBatchCreateModal()")
    expect(owner).to_be_hidden();expect(help).to_be_hidden()
