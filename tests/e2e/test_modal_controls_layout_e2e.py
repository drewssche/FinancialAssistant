import pytest
from playwright.sync_api import expect
from tests.e2e.test_modal_date_layout_e2e import (
    static_server_url, page_with_money_flow_api_mock, open_app,
)
from tests.e2e.modal_layout_assertions import CONTROL_METRICS, assert_controls_fit


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320,390,400,401,640,641,800,1440])
def test_modal_control_bounds_and_sibling_spacing(static_server_url,page_with_money_flow_api_mock,width):
    p=page_with_money_flow_api_mock
    open_app(p,static_server_url,width)
    p.evaluate("window.App.getRuntimeModule('operation-modal').openEditModal({id:42,kind:'expense',amount:'10',currency:'BYN',operation_date:'2026-10-25',receipt_items:[]})")
    p.wait_for_selector('#editModal.operation-editor')
    p.evaluate('async()=>{await document.fonts.ready;await new Promise(requestAnimationFrame);}')
    p.evaluate("document.querySelectorAll('.modal').forEach(n=>n.classList.add('hidden'))")
    # Template-owned dialogs retain their real form layout and initial visibility.
    results=p.evaluate("""()=>{const measure=MEASURE;const results=[];
      for(const root of document.querySelectorAll('.modal')){
        const cl=root.getAttribute('class');root.classList.remove('hidden');
        results.push(measure(root));root.setAttribute('class',cl);
      }return results;
    }""".replace('MEASURE',CONTROL_METRICS))
    assert len(results)>=28
    assert all(not r['overflow'] and not r['issues'] for r in results), [r for r in results if r['overflow'] or r['issues']]
    for mode in ['operation','debt','currency','plan']:
        if mode=='plan':
            p.evaluate("window.App.getRuntimeModule('plans').openCreatePlan()")
            p.locator('[data-plan-schedule-mode="recurring"]').click()
        else:
            p.evaluate("mode=>window.App.getRuntimeModule('operation-modal').openCreateModal({entryMode:mode})",mode)
        assert_controls_fit(p.locator('#createModal'))
    # Both editors must retain the compact refresh icon after currency changes.
    for mode in ['create','edit']:
        prefix='op' if mode=='create' else 'edit'
        p.evaluate("mode=>{document.querySelectorAll('.modal').forEach(n=>n.classList.add('hidden'));document.getElementById(mode+'Modal').classList.remove('hidden');}",mode)
        p.locator(f'#{prefix}Currency').select_option('USD')
        button=p.locator(f'#{prefix}FxRateRefreshBtn')
        expect(button.locator('svg')).to_have_count(1)
        expect(button).to_have_attribute('aria-label','Обновить курс')
        assert_controls_fit(p.locator(f'#{mode}Modal'))
        button.click(trial=True)


@pytest.mark.e2e
def test_rate_refresh_stays_an_icon_while_loading_and_after_error(static_server_url,page_with_money_flow_api_mock):
    p=page_with_money_flow_api_mock
    open_app(p,static_server_url,320)
    p.locator('#opCurrency').select_option('USD')
    p.locator('#opFxRateSourceSwitch [data-fx-rate-source=bank]').click()
    button=p.locator('#opFxRateRefreshBtn')
    expect(button).to_be_enabled()
    pending=[]
    p.route('**/api/v1/currency/rate-options/refresh?*',lambda route:pending.append(route))
    button.click()
    expect(button).to_have_attribute('aria-busy','true')
    expect(button).to_have_attribute('aria-label','Обновляем…')
    expect(button.locator('svg')).to_have_count(1)
    expect(button).to_be_disabled()
    assert_controls_fit(p.locator('#createModal'))
    assert len(pending)==1
    pending[0].fulfill(status=503,json={'detail':'Test quote unavailable'})
    expect(button).to_be_enabled()
    expect(button).to_have_attribute('aria-busy','false')
    expect(button).to_have_attribute('aria-label','Обновить курс')
    expect(button.locator('svg')).to_have_count(1)
