"""Notifications must stay visible and actionable above custom and native modal stacks."""
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock
from tests.e2e.test_operation_editor_ux_e2e import open_editor


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 1440])
@pytest.mark.parametrize('popover', [True, False])
def test_toasts_above_modal_stack_with_actions_and_cleanup(static_server_url, page_with_receipt_api_mock, width, popover):
    p=page_with_receipt_api_mock
    if not popover:
        p.add_init_script('HTMLElement.prototype.showPopover=undefined;HTMLElement.prototype.hidePopover=undefined;')
    open_editor(p,static_server_url,width)
    errors=[]
    p.on('pageerror',lambda error:errors.append(str(error)))
    p.locator('#opNote').focus()
    p.evaluate("window.testToast=window.App.core.notify('Операция обновлена',{type:'success',durationMs:60000})")
    expect(p.locator('#opNote')).to_be_focused()
    toast=p.locator('#toastArea .toast').last

    def assert_front():
        expect(toast).to_be_visible()
        p.wait_for_function("""()=>{
          const button=document.querySelector('#toastArea .toast:last-child button');
          if(!button)return false;const b=button.getBoundingClientRect();
          return button.contains(document.elementFromPoint(b.x+b.width/2,b.y+b.height/2));
        }""")
        b=toast.bounding_box()
        assert b['x']>=0 and b['x']+b['width']<=width+1
        assert b['y']>=0 and b['y']+b['height']<=1000

    assert_front()
    # Opening another custom overlay cannot dim an already visible notice.
    p.evaluate("document.querySelector('#confirmModal').classList.remove('hidden')")
    assert_front()
    p.evaluate("document.querySelector('#confirmModal').classList.add('hidden')")
    # Native modal top-layer order is opening order, not document order.
    for selector in ['#appChoiceDialog','#receiptScanDialog']:
        p.evaluate("selector=>document.querySelector(selector).showModal()",selector)
        assert_front()
        expect(p.locator(selector+' > #toastArea')).to_have_count(1)
    p.evaluate("document.querySelector('#receiptScanDialog').close()")
    assert_front()
    expect(p.locator('#appChoiceDialog > #toastArea')).to_have_count(1)
    toast.locator('[data-toast-close]').click()
    expect(p.locator('#toastArea .toast')).to_have_count(0)
    p.wait_for_function("document.querySelector('#toastArea').parentElement===document.body")
    # Toast creation inside a native modal must not steal keyboard focus.
    choice=p.locator('#appChoiceDialog')
    choice.locator('input').focus()
    p.evaluate("window.App.core.notify('Проверьте сумму',{type:'error',durationMs:60000})")
    expect(choice.locator('input')).to_be_focused()
    assert_front()
    p.screenshot(path=f'/tmp/fa-toast-layers-{width}-{popover}.png')
    toast.locator('[data-toast-close]').click()
    # Undo stays clickable without closing the native modal or duplicating its action.
    p.evaluate("window.undoCount=0;window.App.core.showUndoToast('Позиция удалена',async()=>{window.undoCount++;return 'Отменено';},60000)")
    assert_front()
    toast.locator('[data-toast-undo]').click()
    p.wait_for_function('window.undoCount===1')
    expect(choice).to_be_visible()
    p.evaluate("document.querySelector('#appChoiceDialog').close()")
    assert_front()
    expect(p.locator('body > #toastArea')).to_have_count(1)
    # Automatic expiry hides the top layer, leaving the underlying form interactive.
    p.evaluate("for(const id of [...window.App.state.toasts.keys()])window.App.core.dismissToast(id);window.App.core.notify('Готово',{durationMs:100})")
    expect(p.locator('#toastArea .toast')).to_have_count(0,timeout=5000)
    if popover:
        assert not p.locator('#toastArea').evaluate("n=>n.matches(':popover-open')")
    p.locator('#opNote').fill('Черновик сохранён')
    assert p.locator('#opNote').input_value()=='Черновик сохранён'
    assert errors==[]
