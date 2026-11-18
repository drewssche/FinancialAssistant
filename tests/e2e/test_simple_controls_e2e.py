"""Interaction contracts: searchable choices, explicit units and unchanged historical data."""
import re

import pytest
from playwright.sync_api import expect
from tests.e2e import test_receipt_picker_store_scope_e2e as receipt_fixture
from tests.e2e.test_receipt_picker_store_scope_e2e import _ensure_categories_loaded, _login

static_server_url = receipt_fixture.static_server_url
page_with_receipt_api_mock = receipt_fixture.page_with_receipt_api_mock


def start(page, url, width):
    page.set_viewport_size({'width': width, 'height': 1000})
    page.goto(url + '/static/index.html')
    _login(page)
    _ensure_categories_loaded(page)
    page.click('#addOperationCta')
    expect(page.locator('#createModal')).to_be_visible()


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1440])
def test_searchable_choice_keyboard_escape_and_preview(static_server_url, page_with_receipt_api_mock, width):
    page = page_with_receipt_api_mock
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
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
    search.fill('USD')
    search.press('Enter')
    expect(select).to_have_value('USD')
    expect(dialog).not_to_be_visible()
    # Wrong keyboard layout also works in all select-backed pickers.
    page.evaluate("document.querySelector('#opCurrency').add(new Option('Российский рубль','RUB'))")
    select.click()
    search.fill('hjccbqcrbq')
    expect(dialog.locator('.choice-option')).to_have_count(1)
    dialog.locator('.choice-option').click()
    expect(select).to_have_value('RUB')
    preview = page.locator('#createModal .operation-preview-action')
    expect(preview).to_have_attribute('aria-pressed', 'false')
    preview.click()
    expect(preview).to_have_attribute('aria-pressed', 'true')
    expect(preview).to_have_class(re.compile('is-active'))
    page.screenshot(path=f'/tmp/fa-simple-preview-{width}.png')
    preview.click()
    expect(preview).to_have_attribute('aria-pressed', 'false')
    select.select_option(original)
    expect(page.locator('#createModal .operation-payment-details')).to_have_count(0)
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
    size.locator('[data-sale-unit=piece]').click()
    size.get_by_role('spinbutton').fill('1')
    size.locator('[data-unit=l]').click()
    payload = page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert payload['sale_unit'] == 'piece' and payload['package_unit'] == 'l'
    assert payload['package_quantity'] == '1' and payload['quantity'] == '2' and float(payload['unit_price']) == 3
    page.screenshot(path=f'/tmp/fa-simple-milk-{width}.png')
    size.locator('[data-sale-unit=kg]').click()
    row.locator('[data-receipt-field=quantity]').fill('0.242')
    payload = page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()[0]")
    assert payload['sale_unit'] == 'kg' and payload['package_quantity'] is None and payload['package_unit'] is None
    assert payload['quantity'] == '0.242'
    assert row.locator('.measurement-editor').evaluate('n=>n.scrollWidth<=n.clientWidth+1')


@pytest.mark.e2e
@pytest.mark.parametrize("width", [320, 390, 1440])
def test_purchase_shortcuts_keyboard_and_draft(static_server_url, page_with_receipt_api_mock, width):
    page = page_with_receipt_api_mock
    page.set_viewport_size({"width": width, "height": 844})
    page.goto(static_server_url + "/static/index.html")
    _login(page)
    _ensure_categories_loaded(page)
    scan = page.get_by_role("button", name="Сканировать чек", exact=True)
    scan.click()
    expect(page.locator("#receiptScanDialog")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#createModal")).to_be_hidden()
    expect(scan).to_be_focused()

    add = page.get_by_role("button", name="Добавить операцию", exact=True)
    add.focus()
    add.press("Enter")
    amount = page.locator("#opAmount")
    expect(amount).to_be_focused()
    amount.fill("57.50")
    page.locator("#openReceiptScan").click()
    expect(page.locator("#receiptScanDialog")).to_be_visible()
    page.click("#scanClose")
    expect(page.locator("#createModal")).to_be_visible()
    expect(amount).to_have_value("57.50")

    category = page.locator("#opCategorySearch")
    category.focus()
    picker = page.locator("#createCategoryPickerBlock")
    expect(picker).to_be_visible()
    submit = page.locator("#submitCreateOperationBtn")
    submit.press("Tab")
    expect(picker.get_by_role("button").first).to_be_focused()
    page.keyboard.press("Shift+Tab")
    expect(submit).to_be_focused()
    picker.get_by_role("button").first.press("Escape")
    expect(picker).to_be_hidden()
    expect(category).to_be_focused()
    for key in ["Tab"] * 30 + ["Shift+Tab"] * 30:
        page.keyboard.press(key)
        assert page.evaluate("""() => {
            const modal = document.querySelector('#createModal'), active = document.activeElement;
            const picker = active.closest('.app-popover:not(.hidden)');
            return modal.contains(active) || picker?.__appPopoverOwners?.some(owner => modal.contains(owner));
        }""")
    page.click("#closeCreateModalBtn")
    expect(add).to_be_focused()
    assert page.locator("#batchCreateModal, #batchCategoryModal, #batchItemTemplateModal").count() == 0
    for button in (add, scan):
        rect = button.bounding_box()
        assert rect and 0 <= rect["x"] and rect["x"] + rect["width"] <= width + 1


@pytest.mark.e2e
def test_escape_closes_catalog_row_menu_and_returns_to_trigger(static_server_url, page_with_receipt_api_mock):
    page = page_with_receipt_api_mock
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(static_server_url + "/static/index.html")
    _login(page)
    page.locator("#mainNav button[data-section=item_catalog]").click()
    page.locator('[data-item-catalog-view="sources"]').click()
    page.set_viewport_size({"width": 390, "height": 844})
    trigger = page.locator('#itemCatalogBody [data-mobile-card-menu-trigger^="item-template-"]:visible').first
    trigger.click()
    menu = page.locator(".mobile-card-actions-popover:visible")
    menu.get_by_role("button").first.press("Escape")
    expect(menu).to_have_count(0)
    expect(trigger).to_be_focused()
