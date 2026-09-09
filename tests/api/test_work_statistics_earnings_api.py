from datetime import datetime
from decimal import Decimal

import pytest

from app.api.deps import get_current_user_id
from app.db.models import Operation, User
from app.db.session import get_db
from app.main import app
from app.services import work_service as work_module
from tests.api.test_operations_api import _client_lifecycle


@pytest.fixture
def client(monkeypatch):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 9, 12, 0, tzinfo=tz)

    monkeypatch.setattr(work_module, "datetime", FixedDateTime)
    yield from _client_lifecycle()


def setup_payroll(client):
    category = client.post('/api/v1/categories', json={'name': 'Рабочие выплаты', 'kind': 'income'}).json()['id']
    plan = client.post('/api/v1/plans', json={
        'kind': 'income', 'amount': '1000', 'scheduled_date': '2026-01-05',
        'category_id': category, 'recurrence_enabled': True, 'recurrence_frequency': 'monthly',
    })
    assert plan.status_code == 201, plan.text
    response = client.put('/api/v1/work/profile', json={
        'salary_plan_id': plan.json()['id'], 'salary_nominal_day': 5,
        'standard_hours_per_day': '8', 'workweek_days': [0, 1, 2, 3, 4],
    })
    assert response.status_code == 200, response.text
    return category, plan.json()['id']


def operation(client, when, amount, category=None, **extra):
    response = client.post('/api/v1/operations', json={
        'kind': 'income', 'amount': amount, 'operation_date': when, 'category_id': category, **extra,
    })
    assert response.status_code == 201, response.text
    return response.json()['id']


def link(client, operation_id):
    response = client.post('/api/v1/work/payments/links', json={'operation_id': operation_id, 'role': 'salary'})
    assert response.status_code == 201, response.text
    return response.json()['link_id']


def totals(payload):
    return {row['currency']: Decimal(row['amount']) for row in payload['earnings']['totals']}


def statistics(client, **params):
    response = client.get('/api/v1/work/statistics', params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_statistics_sum_actual_payroll_once_for_each_period_and_month(client):
    category, _ = setup_payroll(client)
    # All-time must include older actual payments without an employment start date.
    operation(client, '2025-12-31', '80', category)
    january = operation(client, '2026-01-01', '100', category)
    link(client, january)  # Matches both category and explicit link, but counts once.
    operation(client, '2026-01-31', '200', category)
    operation(client, '2026-02-01', '50', category)  # Includes payroll extras.
    operation(client, '2026-09-09', '25', category)
    future = operation(client, '2026-09-08', '9000', category)
    link(client, future)
    assert client.patch(f'/api/v1/operations/{future}', json={'operation_date': '2026-09-10'}).status_code == 200
    unrelated = operation(client, '2026-02-02', '9999')
    manual = operation(client, '2026-02-03', '70')
    link(client, manual)
    assert unrelated != manual
    jan = statistics(client, period='month', anchor='2026-01-15')
    assert totals(jan) == {'BYN': Decimal('300.00')}
    assert jan['earnings']['operation_count'] == 2
    year = statistics(client, period='year', anchor='2026-06-15')
    assert totals(year) == {'BYN': Decimal('445.00')}
    assert year['earnings']['operation_count'] == 5
    assert year['earnings']['received_through'] == '2026-09-09'
    month_totals = {row['month']: row['earnings'] for row in year['months']}
    assert month_totals['2026-01'] == [{'currency': 'BYN', 'amount': '300.00'}]
    assert month_totals['2026-02'] == [{'currency': 'BYN', 'amount': '120.00'}]
    assert month_totals['2026-12'] == []
    assert sum(Decimal(value['amount']) for row in year['months'] for value in row['earnings']) == Decimal('445')
    custom = statistics(client, period='custom', date_from='2026-01-31', date_to='2026-02-01')
    assert totals(custom) == {'BYN': Decimal('250.00')}
    assert [row['earnings'][0]['amount'] for row in custom['months']] == ['200.00', '50.00']
    all_time = statistics(client, period='all_time')
    assert all_time['date_from'] == '2025-12-31'
    assert totals(all_time) == {'BYN': Decimal('525.00')}
    assert totals(statistics(client, period='year', anchor='2027-01-01')) == {}


def test_statistics_reflect_edit_delete_restore_and_user_isolation(client):
    category, _ = setup_payroll(client)
    op_id = operation(client, '2026-08-20', '100', category)
    link(client, op_id)
    session_source = app.dependency_overrides[get_db]()
    db = next(session_source)
    try:
        db.add(User(id=2, display_name='Second', status='approved'))
        db.commit()
    finally:
        session_source.close()
    saved_user = app.dependency_overrides[get_current_user_id]
    app.dependency_overrides[get_current_user_id] = lambda: 2
    try:
        other = operation(client, '2026-08-20', '8000')
        link(client, other)
        assert totals(statistics(client, period='year', anchor='2026-01-01')) == {'BYN': Decimal('8000.00')}
    finally:
        app.dependency_overrides[get_current_user_id] = saved_user
    assert totals(statistics(client, period='month', anchor='2026-08-01')) == {'BYN': Decimal('100.00')}
    response = client.patch(f'/api/v1/operations/{op_id}', json={'amount': '150', 'operation_date': '2026-09-01'})
    assert response.status_code == 200, response.text
    assert totals(statistics(client, period='month', anchor='2026-08-01')) == {}
    assert totals(statistics(client, period='month', anchor='2026-09-01')) == {'BYN': Decimal('150.00')}
    assert client.delete(f'/api/v1/operations/{op_id}').status_code == 204
    assert totals(statistics(client, period='year', anchor='2026-01-01')) == {}
    response = client.post(f'/api/v1/operations/{op_id}/restore')
    assert response.status_code == 200, response.text
    assert totals(statistics(client, period='year', anchor='2026-01-01')) == {'BYN': Decimal('150.00')}


def test_statistics_use_conversion_snapshots_and_keep_different_base_currencies_separate(client):
    category, _ = setup_payroll(client)
    operation(client, '2026-08-01', '100', category, currency='USD', fx_rate='3.25')
    separate = operation(client, '2026-08-02', '50', category)
    session_source = app.dependency_overrides[get_db]()
    db = next(session_source)
    try:
        # A historical operation can retain a different base-currency snapshot.
        item = db.get(Operation, separate)
        item.base_currency = 'EUR'
        item.currency = 'EUR'
        db.commit()
    finally:
        session_source.close()
    payload = statistics(client, period='year', anchor='2026-01-01')
    assert totals(payload) == {'BYN': Decimal('325.00'), 'EUR': Decimal('50.00')}
    assert payload['earnings']['operation_count'] == 2


def test_manual_link_does_not_promote_unrelated_category_or_forecasts(client):
    category = client.post('/api/v1/categories', json={'name': 'Прочее', 'kind': 'income'}).json()['id']
    manual = operation(client, '2026-08-01', '100', category)
    link_id = link(client, manual)
    operation(client, '2026-08-02', '900', category)
    assert totals(statistics(client, period='year', anchor='2026-01-01')) == {'BYN': Decimal('100.00')}
    assert client.delete(f'/api/v1/work/payments/links/{link_id}').status_code == 204
    assert totals(statistics(client, period='year', anchor='2026-01-01')) == {}
    setup_payroll(client)
    assert totals(statistics(client, period='year', anchor='2026-01-01')) == {}


def test_confirmed_payroll_category_remains_known_after_plan_deleted(client):
    category, plan_id = setup_payroll(client)
    # Reuse a past confirmed occurrence as durable payroll-category evidence.
    from app.db.models import WorkPaymentLink
    confirmed = operation(client, '2026-01-05', '100', category)
    link_id = link(client, confirmed)
    session_source = app.dependency_overrides[get_db]()
    db = next(session_source)
    try:
        item = db.get(WorkPaymentLink, link_id)
        item.source = 'plan_confirmation'
        item.plan_id = plan_id
        db.commit()
    finally:
        session_source.close()
    operation(client, '2026-02-05', '200', category)
    assert client.delete(f'/api/v1/plans/{plan_id}').status_code == 204
    assert totals(statistics(client, period='year', anchor='2026-01-01')) == {'BYN': Decimal('300.00')}
