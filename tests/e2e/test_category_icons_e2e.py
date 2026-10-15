"""Category icons survive field selection, searching and the shared choice dialog."""
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock
from tests.e2e.test_operation_editor_ux_e2e import open_editor


def assert_field_icon(field, text):
    marker=field.locator('..').locator('.category-field-icon')
    expect(marker).to_have_text(text)
    expect(marker).to_be_visible()
    assert field.evaluate('''n=>{
      const b=n.getBoundingClientRect(),i=n.parentElement.querySelector('.category-field-icon').getBoundingClientRect();
      return i.x>=b.x && i.right<=b.x+parseFloat(getComputedStyle(n).paddingLeft) && i.y>=b.y && i.bottom<=b.bottom;
    }''')


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320,1440])
def test_category_icon_selection_search_group_fallback_and_bulk(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;open_editor(p,static_server_url,width)
    p.evaluate("""() => {
      Object.assign(window.App.state.categories.find(c=>c.id===102),{icon:null,group_icon:'🧭'});
      Object.assign(window.App.state.categories.find(c=>c.id===103),{icon:null,group_icon:null});
    }""")
    field=p.locator('#opCategorySearch')
    field.click();p.locator('#opCategoryAll [data-category-id="101"]').click()
    expect(field).to_have_value('Еда');assert_field_icon(field,'🍔')
    expect(p.locator('#opCategory')).to_have_value('101')
    field.fill('Транс')
    expect(field).to_be_focused()
    expect(field.locator('..').locator('.category-field-icon')).to_be_hidden()
    p.locator('#opCategoryAll [data-category-id="102"]').click()
    expect(field).to_have_value('Транспорт');assert_field_icon(field,'🧭')
    p.screenshot(path=f'/tmp/fa-category-selected-{width}.png')
    field.fill('Коф');p.locator('#opCategoryAll [data-category-id="103"]').click()
    expect(field).to_have_value('Кофе')
    expect(field.locator('..').locator('.category-field-icon')).to_be_hidden()
    expect(p.locator('#opCategory')).to_have_value('103')
    p.screenshot(path=f'/tmp/fa-category-field-{width}.png')
    p.keyboard.press('Escape')
    expect(p.locator('#createModal')).to_be_hidden()
    p.evaluate("""() => {
      const bulk=window.App.getRuntimeModule('bulk-ui');
      bulk.fillBulkOperationCategorySelect('expense');bulk.openBulkEditOperationsModal();
    }""")
    select=p.locator('#bulkOpCategory');select.click()
    picker=p.locator('#appChoiceDialog')
    expect(picker.get_by_role('button',name='Еда',exact=True).locator('.category-chip-icon')).to_have_text('🍔')
    choice=picker.get_by_role('button',name='Транспорт',exact=True)
    expect(choice.locator('.category-chip-icon')).to_have_text('🧭')
    expect(picker.get_by_role('button',name='Кофе',exact=True).locator('.category-chip-icon')).to_have_count(0)
    picker.screenshot(path=f'/tmp/fa-category-picker-{width}.png')
    choice.click()
    expect(select).to_have_value('102')
    expect(select.locator('option:checked')).to_have_text('🧭 Транспорт')
