"""Shared dashboard/section layouts preserve actions and fit mobile/desktop screens."""
from datetime import date

import pytest
from playwright.sync_api import expect
from tests.e2e.test_plans_ui_e2e import static_server_url, page_with_plans_api_mock, _login_and_open_dashboard


@pytest.mark.e2e
@pytest.mark.parametrize('width', [320, 390, 1024, 1440, 2338])
def test_compact_bank_quotes_above_plans_and_plan_grid(static_server_url, page_with_plans_api_mock, width):
    page, state = page_with_plans_api_mock
    page.set_viewport_size({'width': width, 'height': 1000})
    today = date.today().isoformat()
    state['plans'][:] = [dict(id=i, kind='expense', amount='2.99', scheduled_date=today,
        note='' if i != 2 else 'Оплата подписки с длинным комментарием для проверки переноса строки',
        recurrence_enabled=True, recurrence_frequency='monthly', recurrence_interval=1,
        recurrence_weekdays=[], recurrence_workdays_only=False, recurrence_month_end=False,
        recurrence_end_date=None, status='upcoming', confirm_count=0, skip_count=0,
        next_reminder_at=today+'T09:00:00Z') for i in range(1, 4)]
    state['plans'][0].update(category_name='Кофе')
    state['plans'][1].update(currency='EUR',base_currency='BYN',original_amount='23.00',amount='77.74',
        fx_rate_source='bank',fx_bank_code='technobank',fx_bank_name='Технобанк',fx_bank_channel='cash',
        fx_rate_kind='sell',fx_payment_mode='direct_conversion',current_rate='3.38',current_rate_date=today,
        current_base_amount='77.74', receipt_items=[dict(name='Подписка', quantity='1', unit_price='23', line_total='23')])
    state['preferences']['data']['currency'] = {'tracked_currencies': ['USD', 'EUR', 'RUB']}
    def banks(buy, sell):
        return [
            dict(bank_name='Приорбанк', channel_label='онлайн', buy_unit_rate=buy, sell_unit_rate=sell,
                 quoted_at=today+'T09:00:00Z', stale=True),
            dict(bank_name='Технобанк', channel_label='наличные', buy_unit_rate=buy, sell_unit_rate=sell,
                 fetched_at=today+'T10:00:00Z'),
            dict(bank_name='БСБ Банк', channel_label='наличные'),
            dict(bank_name='Сбер Банк', channel_label='наличные', buy_unit_rate=buy, sell_unit_rate=sell,
                 fetched_at=today+'T10:00:00Z'),
        ]
    page.route('**/api/v1/dashboard/currency-rates', lambda route: route.fulfill(json=[
        dict(currency='USD', display_rate='3.0091', display_scale=1, change_pct=-0.07, rate_date=today, bank_rates=banks('2.99', '3.05')),
        dict(currency='EUR', display_rate='3.3749', display_scale=1, change_pct=0.13, rate_date=today, bank_rates=banks('3.32', '3.41')),
        dict(currency='RUB', display_rate='3.6038', display_scale=100, change_pct=0.08, rate_date=today, bank_rates=banks('.0351', '.0368')),
    ]))
    page.route('**/api/v1/operations/catalog-products*', lambda route: route.fulfill(json={'items':[], 'total':0, 'page':1, 'page_size':100}))
    _login_and_open_dashboard(page, static_server_url)
    expect(page.locator('#dashboardPlansList .plan-card')).to_have_count(3)
    assert page.locator('#dashboardSection').evaluate("n=>n.firstElementChild.id") == 'dashboardAnalyticsPanel'
    panel = page.locator('#dashboardCurrencyPanel')
    plans = page.locator('#dashboardCurrencyPanel + #dashboardPlansPanel')
    expect(plans).to_be_visible()
    rates = panel.locator('[data-dashboard-quote]')
    expect(rates).to_have_count(3)
    expect(panel.get_by_role('button')).to_have_count(3)
    tables = panel.get_by_role('table')
    expect(tables).to_have_count(3)
    rub = panel.get_by_role('table', name='Курсы банков в BYN за 100 RUB')
    expect(rub.get_by_role('columnheader')).to_have_text(['Банк · BYN', 'Я покупаю', 'Я продаю'])
    expect(rub.get_by_role('row', name='Технобанк', exact=False).get_by_role('cell')).to_have_text(['3,68', '3,51'])
    expect(rub.get_by_role('row', name='БСБ Банк', exact=False).get_by_role('cell')).to_have_text(['—', '—'])
    expect(rub.get_by_role('rowheader', name='Приорбанк устарел')).to_be_visible()
    expect(panel.locator('[data-dashboard-quote=RUB]')).to_contain_text('100 RUB')
    expect(panel.locator('#dashboardCurrencyDate')).to_have_text('НБРБ на '+date.today().strftime('%d.%m.%Y'))
    for row in rates.all():
        assert row.evaluate('n => n.scrollWidth <= n.clientWidth + 1')
        assert row.bounding_box()['height'] >= 44
    for table in tables.all():
        expect(table.get_by_role('row')).to_have_count(5)
        assert table.evaluate('t => [...t.querySelectorAll("th, td")].every(c => c.scrollWidth <= c.clientWidth + 1)')
        assert table.evaluate('t => t.getBoundingClientRect().right <= innerWidth && t.offsetWidth <= t.parentElement.clientWidth + 1')
    box = panel.bounding_box()
    assert box['y'] + box['height'] <= plans.bounding_box()['y'] + 1
    assert box['height'] < (665 if width < 640 else 450 if width == 1024 else 267)
    panel.screenshot(path=f'/tmp/fa-currency-kpi-{width}.png')
    layouts=[]
    for section, selector in [('dashboard','#dashboardPlansList'),('plans','#plansList')]:
        page.evaluate("name=>window.App.getRuntimeModule('navigation').switchSection(name)",section)
        cards=page.locator(selector+' .plan-card')
        expect(cards).to_have_count(3)
        expect(cards.get_by_role('heading', name='Подписка', exact=True)).to_have_count(1)
        expect(cards.get_by_role('heading', name='Кофе', exact=True)).to_have_count(1)
        expect(cards.get_by_role('button', name='Записать расход')).to_have_count(3)
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


@pytest.mark.e2e
@pytest.mark.parametrize('width,code', [(390, 'EUR'), (1440, 'RUB')])
def test_dashboard_opens_banks_for_selected_currency(static_server_url, page_with_plans_api_mock, width, code):
    page, state = page_with_plans_api_mock
    page.set_viewport_size({'width': width, 'height': 844})
    state['preferences']['data']['currency'] = {'tracked_currencies': ['USD', 'EUR', 'RUB']}
    rows = [
        dict(currency='USD', display_scale=1, display_rate='3', change_pct=0, rate_date='2026-01-08', bank_rates=[]),
        dict(currency='EUR', display_scale=1, display_rate=None, change_pct=None, rate_date=None, bank_rates=[
            dict(bank_name='Технобанк', channel_label='наличные', buy_unit_rate='3.29', sell_unit_rate='3.49',
                 fetched_at='2026-01-08T09:00:00Z'),
        ]),
        dict(currency='RUB', display_scale=100, display_rate='3.52', change_pct=None, rate_date='2026-01-07'),
    ]
    page.route('**/api/v1/dashboard/currency-rates', lambda route: route.fulfill(json=rows))
    overview_calls = []
    page.on('request', lambda req: overview_calls.append(req.url) if '/currency/overview' in req.url else None)
    _login_and_open_dashboard(page, static_server_url)
    panel = page.locator('#dashboardCurrencyPanel')
    expect(panel.locator('[data-dashboard-quote=USD]')).to_contain_text('08.01.2026')
    expect(panel.locator('[data-dashboard-quote=RUB]')).to_contain_text('07.01.2026')
    expect(panel.locator('[data-dashboard-quote=EUR]')).to_contain_text('Нет курса')
    expect(panel.get_by_role('table')).to_have_count(1)
    expect(panel.get_by_role('table', name='Курсы банков в BYN за 1 EUR').get_by_role('cell')).to_have_text(['3,49', '3,29'])
    expect(panel.locator('#dashboardCurrencyDate')).to_be_empty()
    assert not overview_calls

    # A previous visit to the exchange journal must not override the chosen bank view.
    page.evaluate("window.App.getRuntimeModule('currency').setCurrencyView('portfolio', {load: false})")
    panel.locator(f'[data-dashboard-quote={code}]').click()
    expect(page.locator('[data-currency-view=rates]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator(f'[data-quote-currency={code}]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#currencyQuotesList caption')).to_have_text(f"BYN за {100 if code == 'RUB' else 1} {code}")
    expect(page.locator('#currencyQuotesList')).to_contain_text('Технобанк')
    expect(page.locator('#currencyQuotesList')).to_contain_text('Я покупаю')


@pytest.mark.e2e
def test_hidden_dashboard_rates_skip_currency_requests(static_server_url, page_with_plans_api_mock):
    page, state = page_with_plans_api_mock
    state['preferences']['data']['currency'] = {'show_dashboard_kpi': False, 'tracked_currencies': ['USD']}
    requests = []
    page.on('request', lambda req: requests.append(req.url))
    with page.expect_request('**/api/v1/dashboard/debts/preview*'):
        _login_and_open_dashboard(page, static_server_url)
    expect(page.locator('#dashboardCurrencyPanel')).to_be_hidden()
    assert not any('/dashboard/currency-rates' in url or '/currency/overview' in url for url in requests)


@pytest.mark.e2e
def test_dashboard_rates_retry_loads_quotes_and_keeps_last_publication_on_error(static_server_url, page_with_plans_api_mock):
    page, _ = page_with_plans_api_mock
    calls = []

    def rates(route):
        calls.append(route.request.method)
        if len(calls) != 2:
            return route.fulfill(status=503, json={'detail': 'Недоступно'})
        return route.fulfill(json=[dict(currency='USD', display_scale=1, display_rate='3.2',
                                        rate_date='2026-01-08', change_pct=None, bank_rates=[
                                            dict(bank_name='БСБ Банк', channel_label='наличные',
                                                 buy_unit_rate='3.18', sell_unit_rate='3.25',
                                                 fetched_at='2026-01-08T09:00:00Z'),
                                        ])])

    page.route('**/api/v1/dashboard/currency-rates', rates)
    _login_and_open_dashboard(page, static_server_url)
    panel = page.locator('#dashboardCurrencyPanel')
    expect(panel.get_by_role('alert')).to_contain_text('Не удалось загрузить курсы валют')
    panel.get_by_role('button', name='Повторить загрузку').click()
    expect(panel.locator('[data-dashboard-quote=USD]')).to_contain_text('3,2000')
    page.evaluate("window.App.getRuntimeModule('dashboard').loadDashboard()")
    expect(panel).to_have_attribute('data-load-state', 'stale')
    expect(panel.locator('#dashboardCurrencyDate')).to_have_text('НБРБ на 08.01.2026')
    expect(panel.locator('[data-dashboard-quote=USD]')).to_contain_text('3,2000')
    expect(panel.get_by_role('cell')).to_have_text(['3,25', '3,18'])
    assert calls == ['GET', 'GET', 'GET']
