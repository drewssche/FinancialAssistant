"""Measure rendered date text and controls, including widths between breakpoints."""
import pytest
from playwright.sync_api import expect
from tests.e2e.test_operations_money_flow_e2e import (
    static_server_url, page_with_money_flow_api_mock, _open_app,
)

DATE_METRICS = """input => {
  const r=input.getBoundingClientRect(), s=getComputedStyle(input);
  const canvas=document.createElement('canvas').getContext('2d');canvas.font=s.font;
  const available=input.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight);
  const needed=canvas.measureText('25.10.2026').width+12;
  const wrap=input.closest('.date-input-wrap');
  const buttons=[...(wrap?.querySelectorAll('button')||[])]
    .filter(n=>n.getBoundingClientRect().width).map(n=>{
      const b=n.getBoundingClientRect();
      return {button:n.className,fit:b.left>=r.left+3&&b.right<=r.right-3&&b.top>=r.top+3&&b.bottom<=r.bottom-3};
    });
  return {id:input.id,available,needed,buttons,
    fits:r.width>0&&available>=needed&&r.left>=0&&r.right<=innerWidth&&buttons.every(b=>b.fit)};
}"""


def open_app(page, url, width):
    page.set_viewport_size({'width':width,'height':950})
    page.route('**/api/v1/operations/catalog-products?*',lambda r:r.fulfill(json=[]))
    _open_app(page,url)
    page.evaluate("window.App.getRuntimeModule('operation-modal').openCreateModal()")
    page.wait_for_selector('#createModal.operation-editor')
    page.wait_for_selector('#scanDate', state='attached')
    page.evaluate('async()=>{await document.fonts.ready;await new Promise(requestAnimationFrame);}')


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320,390,640,641,700,800,900,1440])
def test_all_modal_date_layouts(static_server_url, page_with_money_flow_api_mock, width):
    page = page_with_money_flow_api_mock
    open_app(page, static_server_url, width)
    page.evaluate("window.App.getRuntimeModule('operation-modal').openEditModal({id:42,kind:'expense',amount:'10',currency:'BYN',operation_date:'2026-10-25',receipt_items:[]})")
    page.wait_for_selector('#editModal.operation-editor')
    page.evaluate("document.querySelectorAll('.modal').forEach(n=>n.classList.add('hidden'))")
    # Reveal each optional field in its original layout without changing its grid
    # or opening unrelated siblings (e.g. recurrence and price-history filters).
    result = page.evaluate("""measure => {
      const results=[];
      for(const input of document.querySelectorAll('.modal input[type="date"], dialog input[type="date"]')) {
        const saved=[];
        for(let n=input;n && n!==document.body;n=n.parentElement) {
          saved.push([n,n.getAttribute('class'),n.getAttribute('style'),n.hasAttribute('hidden'),n.hasAttribute('open')]);
          n.classList.remove('hidden');n.removeAttribute('hidden');
          if(n instanceof HTMLDialogElement)n.open=true;
          if(n.style.display==='none') n.style.removeProperty('display');
        }
        const value=input.value;input.value='2026-10-25';
        results.push(measure(input));input.value=value;
        for(const [n,cl,st,hidden,open] of saved){
          cl===null?n.removeAttribute('class'):n.setAttribute('class',cl);
          st===null?n.removeAttribute('style'):n.setAttribute('style',st);
          n.toggleAttribute('hidden',hidden);n.toggleAttribute('open',open);
        }
      } return results;
    }""".replace('measure => {', '() => { const measure = ' + DATE_METRICS + ';'))
    assert len(result) >= 19  # All template fields plus the dynamically mounted scan.
    assert all(r['fits'] for r in result), [r for r in result if not r['fits']]


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320,641,700,1440])
def test_date_controls_in_active_editor_modes(static_server_url, page_with_money_flow_api_mock, width, tmp_path):
    page = page_with_money_flow_api_mock
    open_app(page,static_server_url,width)
    for mode in ['operation','debt','currency','plan']:
        if mode == 'plan':
            page.evaluate("window.App.getRuntimeModule('plans').openCreatePlan()")
            page.locator('[data-plan-schedule-mode="recurring"]').click()
        else:
            page.evaluate("mode=>window.App.getRuntimeModule('operation-modal').openCreateModal({entryMode:mode})",mode)
        dates=page.locator('#createModal input[type="date"]:visible')
        assert dates.count() > 0
        for date in dates.all():
            date.fill('2026-10-25')
            metrics=date.evaluate(DATE_METRICS)
            assert metrics['fits'], (mode,width,metrics)
            field_id=date.get_attribute('id')
            trigger=page.locator(f'[data-date-picker-trigger="{field_id}"]')
            # Verify the calendar button invokes the picker of the correct input.
            date.evaluate("n=>{n.showPicker=()=>{n.dataset.pickerOpened='yes';};}")
            trigger.click()
            expect(date).to_have_attribute('data-picker-opened','yes')
            next_day=page.locator(f'[data-date-step-target="{field_id}"][data-date-step="1"]')
            if next_day.count() and next_day.is_visible():
                next_day.click()
                expect(date).to_have_value('2026-10-26')
        card=page.locator('#createModal .modal-card')
        assert card.evaluate('n=>n.scrollWidth<=n.clientWidth+1'), (mode,width)
        page.screenshot(path=str(tmp_path/f'{mode}-{width}.png'))
