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
        note='Подписка' if i != 2 else 'Оплата подписки с длинным комментарием для проверки переноса строки',
        recurrence_enabled=True, recurrence_frequency='monthly', recurrence_interval=1,
        recurrence_weekdays=[], recurrence_workdays_only=False, recurrence_month_end=False,
        recurrence_end_date=None, status='upcoming', confirm_count=0, skip_count=0,
        next_reminder_at=today+'T09:00:00Z') for i in range(1, 4)]
    page.route('**/api/v1/operations/catalog-products*', lambda route: route.fulfill(json={'items':[], 'total':0, 'page':1, 'page_size':100}))
    _login_and_open_dashboard(page, static_server_url)
    expect(page.locator('#dashboardPlansList .plan-card')).to_have_count(3)
    assert page.locator('#dashboardSection').evaluate("n=>n.firstElementChild.id") == 'dashboardCurrencyPanel'
    layouts=[]
    for section, selector in [('dashboard','#dashboardPlansList'),('plans','#plansList')]:
        page.evaluate("name=>window.App.getRuntimeModule('navigation').switchSection(name)",section)
        cards=page.locator(selector+' .plan-card')
        expect(cards).to_have_count(3)
        cards.first.scroll_into_view_if_needed()
        for card in cards.all():
            box=card.bounding_box()
            assert box['x']>=0 and box['x']+box['width']<=width+1
            if width>=1440: assert box['width']<750
            for child in card.locator('button, .plan-card-amount, .plan-card-date, .plan-card-top-meta').all():
                b=child.bounding_box()
                assert b['x']>=box['x']-1 and b['x']+b['width']<=box['x']+box['width']+1
            assert card.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
        layouts.append(cards.first.locator('.plan-card-row').evaluate('n=>getComputedStyle(n).gridTemplateAreas'))
        page.locator('#dashboardPlansPanel' if section=='dashboard' else '#plansList').screenshot(path=f'/tmp/fa-{section}-cards-{width}.png',animations='disabled')
    assert layouts[0]==layouts[1]
    page.locator('#plansList [data-plan-action=edit]').first.click()
    expect(page.locator('#createModal')).to_be_visible()
