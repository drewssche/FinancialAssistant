from decimal import Decimal

import pytest

from tests.api.test_catalog_products_api import client  # noqa: F401
from app.api.deps import get_current_user_id
from app.main import app


def product(client, name='Товар', **extra):
    response = client.post('/api/v1/operations/catalog-products', json={'name': name, **extra})
    assert response.status_code == 201, response.text
    return response.json()['id']


def line(product_id, **extra):
    return {'product_id': product_id, 'name': 'Товар', 'shop_name': 'Магазин А',
            'quantity': '1', 'unit_price': '10', 'sale_unit': None,
            'package_quantity': None, 'package_unit': None, 'discount_mode': None, 'discount_value': None, **extra}


def operation(client, lines, **extra):
    response = client.post('/api/v1/operations', json={'kind': 'expense', 'operation_date': '2026-10-12', 'receipt_items': lines, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def positions(client, period='month'):
    response = client.get('/api/v1/dashboard/analytics/positions', params={'period': period, 'anchor': '2026-10-12'})
    assert response.status_code == 200, response.text
    return response.json()


def highlights(client):
    response = client.get('/api/v1/dashboard/analytics/highlights', params={'month': '2026-10'})
    assert response.status_code == 200, response.text
    return response.json()


def number(totals, key):
    return Decimal(totals[key])


@pytest.mark.parametrize('period', ['day', 'week', 'month', 'year'])
def test_product_and_summary_count_receipts_not_rows_or_offers(client, period):
    first, second = product(client), product(client, 'Второй')
    operation(client, [line(first), line(first), line(first, shop_name='Магазин Б'), line(second, name='Второй')])
    operation(client, [line(first, shop_name='Магазин Б')])
    data = positions(client, period)
    row = next(item for item in data['positions'] if item['product_id'] == first)
    assert row['purchases_count'] == 2
    assert row['quantity_totals']['rows_count'] == 4
    assert row['quantity_totals']['unknown_rows_count'] == 4
    assert row['sources_count'] == 2
    assert sum(bucket['purchases_count'] for bucket in row['buckets']) == 2
    assert data['summary']['purchases_count'] == 2  # not the sum of 2 + 1 across products
    assert data['summary']['quantity_totals']['rows_count'] == 5
    assert number(data['summary']['amount_totals'], 'BYN') == 50
    assert highlights(client)['frequent_positions'][0]['product_id'] == first


def test_measurements_are_comparable_snapshot_totals_with_partial_coverage(client):
    item = product(client)
    operation(client, [
        line(item, quantity='2', sale_unit='pack', package_quantity='900', package_unit='g'),
        line(item, quantity='0.242', sale_unit='kg'),
        line(item, quantity='250', sale_unit='g'),
        line(item, quantity='2', sale_unit='piece', package_quantity='750', package_unit='ml'),
        line(item, quantity='0.4', sale_unit='l'),
        line(item, quantity='100', sale_unit='ml'),
        line(item, quantity='3', sale_unit='pack', package_quantity='10', package_unit='piece'),
        line(item, quantity='4', sale_unit='piece'),
        line(item, quantity='8', sale_unit='pack'),
        line(item, quantity='99999'),  # unknown does not become pieces or kg
    ])
    # Changing current catalog metadata must never rewrite old measurement snapshots.
    response = client.patch(f'/api/v1/operations/catalog-products/{item}', json={
        'sale_unit': 'pack', 'package_quantity': '500', 'package_unit': 'g',
    })
    assert response.status_code == 200, response.text
    row = positions(client)['positions'][0]
    q = row['quantity_totals']
    assert number(q, 'packs') == 13
    assert number(q, 'pieces') == 6
    assert number(q, 'mass_kg') == Decimal('2.292')
    assert number(q, 'volume_l') == Decimal('2')
    assert number(q, 'content_pieces') == 30
    assert q['rows_count'] == 10 and q['unknown_rows_count'] == 1
    assert q['unmeasured_package_rows_count'] == 2
    assert highlights(client)['frequent_positions'][0]['quantity_totals'] == q


def test_frequency_ranking_excludes_income_and_future_plans(client):
    rare, frequent = product(client, 'Редкий'), product(client, 'Частый')
    operation(client, [line(rare, name='Редкий', quantity='90000')])
    for _ in range(2):
        operation(client, [line(frequent, name='Частый', quantity='0.1', sale_unit='kg')])
    operation(client, [line(rare, name='Редкий', quantity='99999')], kind='income')
    plan = client.post('/api/v1/plans', json={'kind': 'expense', 'scheduled_date': '2026-10-12', 'receipt_items': [line(rare)]})
    assert plan.status_code == 201
    rows = highlights(client)['frequent_positions']
    assert rows[0]['product_id'] == frequent and rows[0]['purchases_count'] == 2
    assert rows[1]['purchases_count'] == 1
    assert positions(client)['summary']['purchases_count'] == 3


def test_original_currencies_remain_separate_and_paid_totals_exact(client):
    item = product(client)
    operation(client, [line(item, quantity='0.242', unit_price='15.64', regular_unit_price='15.64',
                            sale_unit='kg', is_discounted=True, discount_mode='amount', discount_value='0.13')])
    operation(client, [line(item, quantity='2')], currency='USD', fx_rate='3.5', fx_rate_source='manual')
    data = positions(client)
    amounts = data['positions'][0]['amount_totals']
    assert number(amounts, 'BYN') == Decimal('3.65')
    assert number(amounts, 'USD') == 20
    assert data['summary']['amount_totals'] == amounts
    assert highlights(client)['frequent_positions'][0]['amount_totals'] == amounts


def test_edit_delete_restore_and_cache_invalidation_preserve_counts(client):
    item = product(client)
    purchase = operation(client, [line(item, sale_unit='pack', quantity='2', package_quantity='900', package_unit='g')])
    assert number(positions(client)['summary']['quantity_totals'], 'mass_kg') == Decimal('1.8')
    changed = client.patch(f"/api/v1/operations/{purchase['id']}", json={'receipt_items': [line(item, sale_unit='kg', quantity='0.242')], 'amount': None})
    assert changed.status_code == 200, changed.text
    assert number(positions(client)['summary']['quantity_totals'], 'mass_kg') == Decimal('0.242')
    assert client.delete(f"/api/v1/operations/{purchase['id']}").status_code == 204
    assert positions(client)['summary']['purchases_count'] == 0
    assert client.post(f"/api/v1/operations/{purchase['id']}/restore").status_code == 200
    assert positions(client)['summary']['purchases_count'] == 1
    assert number(positions(client)['summary']['quantity_totals'], 'mass_kg') == Decimal('0.242')


def test_metrics_are_user_scoped(client):
    item = product(client)
    operation(client, [line(item, sale_unit='kg', quantity='4')])
    assert positions(client)['summary']['purchases_count'] == 1
    app.dependency_overrides[get_current_user_id] = lambda: 98765
    try:
        result = positions(client)
        assert result['positions'] == []
        assert result['summary']['purchases_count'] == 0
    finally:
        app.dependency_overrides[get_current_user_id] = lambda: 1


def test_discount_purchase_counts_deduplicate_repeated_lines(client):
    item = product(client)
    discounted = line(item, quantity='2', unit_price='1', regular_unit_price='2', is_discounted=True, discount_type='promo')
    operation(client, [discounted, discounted])
    row = highlights(client)['top_discount_savings'][0]
    assert row['purchases_count'] == 1
    assert row['type_breakdown'][0]['purchases_count'] == 1
    assert row['timeline'][0]['purchases_count'] == 1
    assert Decimal(row['savings_total']) == 4
