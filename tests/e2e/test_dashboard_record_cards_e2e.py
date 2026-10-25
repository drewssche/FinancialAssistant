"""Shared dashboard/section layouts preserve actions and fit mobile/desktop screens."""
from datetime import date

import pytest
from playwright.sync_api import expect
from tests.e2e.test_plans_ui_e2e import static_server_url, page_with_plans_api_mock, _login_and_open_dashboard


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1024, 1440, 2338])
def test_plan_cards_share_compact_grid_and_currency_is_first(static_server_url, page_with_plans_api_mock, width):
    page, state = page_with_plans_api_mock
    page.set_viewport_size({'width': width, 'height': 1000})
    today = date.today().isoformat()
    state['plans'][:] = [dict(id=i, kind='expense', amount='2.99', scheduled_date=today,
        note='' if i != 2 else 'Оплата подписки с длинным комментарием для проверки переноса строки',
        recurrence_enabled=True, recurrence_frequency='monthly', recurrence_interval=1,
        recurrence_weekdays=[], recurrence_workdays_only=False, recurrence_month_end=False,
        recurrence_end_date=None, status='upcoming', confirm_count=0, skip_count=0,
        next_reminder_at=today+'T09:00:00Z') for i in range(1, 4)]
    state['plans'][1].update(currency='EUR',base_currency='BYN',original_amount='23.00',amount='77.74',
        fx_rate_source='bank',fx_bank_code='technobank',fx_bank_name='Технобанк',fx_bank_channel='cash',
        fx_rate_kind='sell',fx_payment_mode='direct_conversion',current_rate='3.38',current_rate_date=today,
        current_base_amount='77.74', receipt_items=[dict(name='Подписка', quantity='1', unit_price='23', line_total='23')])
    page.route('**/api/v1/currency/overview?*',lambda route:route.fulfill(json={
        'tracked_currencies':['USD','EUR','RUB'], 'current_rates':[
            dict(currency=c,rate=r,change_value=d,change_percent='.13',rate_date=today,source='nbrb_auto_unit')
            for c,r,d in [('USD','3.0091','-.0022'),('EUR','3.3749','.0043'),('RUB','.036038','.000028')]],
        'bank_rates':[dict(currency=c,bank_code=b,bank_name=n,buy_rate=buy,sell_rate=sell,scale=100 if c=='RUB' else 1,stale=False) for c in ['USD','EUR','RUB'] for b,n,buy,sell in [('technobank','Технобанк','3.1','3.2'),('bsb','БСБ Банк','3.05','3.25')]]}))
    page.route('**/api/v1/operations/catalog-products*', lambda route: route.fulfill(json={'items':[], 'total':0, 'page':1, 'page_size':100}))
    _login_and_open_dashboard(page, static_server_url)
    expect(page.locator('#dashboardPlansList .plan-card')).to_have_count(3)
    assert page.locator('#dashboardSection').evaluate("n=>n.firstElementChild.id") == 'dashboardAnalyticsPanel'
    rates=page.locator('#dashboardCurrencyRates .dashboard-currency-rate-card')
    expect(rates).to_have_count(3)
    for rate in rates.all():
        assert rate.evaluate("n=>{const s=getComputedStyle(n);return parseFloat(s.borderLeftWidth)>0&&parseFloat(s.borderRadius)>0&&s.backgroundColor!=='rgba(0, 0, 0, 0)';}")
    for rate in rates.all():
        bank_rows=rate.locator('.dashboard-bank-rate-row')
        expect(bank_rows).to_have_count(3)
        expect(bank_rows.first).to_contain_text('Покупка')
        expect(bank_rows.first).to_contain_text('Продажа')
        for bank in bank_rows.all():
            expect(bank).to_be_visible()
            assert bank.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
        expect(bank_rows.nth(1)).to_contain_text('Технобанк')
        expect(bank_rows.nth(1).locator('strong').first).to_contain_text('3.1')
    page.locator('#dashboardCurrencyPanel').screenshot(path=f'/tmp/fa-currency-kpi-{width}.png')
    layouts=[]
    for section, selector in [('dashboard','#dashboardPlansList'),('plans','#plansList')]:
        page.evaluate("name=>window.App.getRuntimeModule('navigation').switchSection(name)",section)
        cards=page.locator(selector+' .plan-card')
        expect(cards).to_have_count(3)
        expect(cards.locator('[data-plan-receipt-view-id]')).to_have_count(1)
        cards.first.scroll_into_view_if_needed()
        for card in cards.all():
            box=card.bounding_box()
            assert box['x']>=0 and box['x']+box['width']<=width+1
            if width>=1440: assert box['width']<750
            for child in card.locator('button, .plan-card-amount, .plan-card-date, .plan-card-top-meta').all():
                b=child.bounding_box()
                assert b['x']>=box['x']-1 and b['x']+b['width']<=box['x']+box['width']+1
            assert card.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
        # Adjacent cards share rows despite missing notes, long FX explanations,
        # and the receipt button making one category row taller.
        rows = cards.evaluate_all("""cards => cards.map(c => {
            const y = s => c.querySelector(s)?.getBoundingClientRect().top;
            return {top:c.getBoundingClientRect().top, height:c.getBoundingClientRect().height,
                category:y('.kind-pill'), meta:y('.plan-card-top-meta'), reminder:y('.meta-chip')};
        })""")
        for row in rows:
            peers = [r for r in rows if abs(r['top'] - row['top']) < 2]
            for key in ('height', 'category', 'meta', 'reminder'):
                values = [r[key] for r in peers if r[key] is not None]
                assert not values or max(values) - min(values) < 2, (section, width, key, peers)
        offsets=cards.evaluate_all("cards=>cards.map(c=>c.querySelector('.plan-card-date').getBoundingClientRect().top-c.getBoundingClientRect().top)")
        assert max(offsets)-min(offsets)<2
        layouts.append(cards.first.locator('.plan-card-row').evaluate('n=>getComputedStyle(n).gridTemplateAreas'))
        page.locator('#dashboardPlansPanel' if section=='dashboard' else '#plansList').screenshot(path=f'/tmp/fa-{section}-cards-{width}.png',animations='disabled')
    assert layouts[0]==layouts[1]
    page.locator('#plansList [data-plan-action=edit]').first.click()
    expect(page.locator('#createModal')).to_be_visible()
