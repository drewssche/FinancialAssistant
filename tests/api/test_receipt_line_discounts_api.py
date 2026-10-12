from decimal import Decimal

import pytest

from tests.api.test_catalog_products_api import client  # noqa: F401


def line(**extra):
    return dict(name='Сыр весовой', quantity='0.242', unit_price='15.64',
                regular_unit_price='15.64', is_discounted=True, discount_type='coupon',
                discount_mode='amount', discount_value='0.13',
                sale_unit='kg', package_quantity=None, package_unit=None) | extra


def create(client, item, *, plan=False):
    response = client.post('/api/v1/plans' if plan else '/api/v1/operations', json={
        'kind': 'expense', 'scheduled_date' if plan else 'operation_date': '2026-10-12',
        'receipt_items': [item],
    })
    assert response.status_code == 201, response.text
    return response.json()


def assert_total(payload, total, subtotal='3.78'):
    row = payload['receipt_items'][0]
    assert Decimal(row['line_total']) == Decimal(total)
    assert Decimal(payload['receipt_total']) == Decimal(total)
    assert Decimal(payload['amount']) == Decimal(total)
    assert (None if row['line_subtotal'] is None else Decimal(row['line_subtotal'])) == (None if subtotal is None else Decimal(subtotal))
    return row


@pytest.mark.parametrize(('mode', 'value', 'total'), [('amount', '0.13', '3.65'), ('percent', '10', '3.40'), ('final', '3.65', '3.65')])
def test_weighted_exact_discount_roundtrip_and_restore(client, mode, value, total):
    purchase = create(client, line(discount_mode=mode, discount_value=value))
    row = assert_total(purchase, total)
    assert abs(Decimal(row['unit_price']) - Decimal(total) / Decimal('0.242')) < Decimal('0.000001')
    updated = client.patch(f"/api/v1/operations/{purchase['id']}", json={'receipt_items': [row], 'amount': None})
    assert updated.status_code == 200, updated.text
    assert_total(updated.json(), total)
    assert client.delete(f"/api/v1/operations/{purchase['id']}").status_code == 204
    restored = client.post(f"/api/v1/operations/{purchase['id']}/restore")
    assert restored.status_code == 200, restored.text
    saved = assert_total(restored.json(), total)
    assert saved['discount_mode'] == mode
    assert Decimal(saved['discount_value']) == Decimal(value)
    assert saved['discount_type'] == 'coupon'


@pytest.mark.parametrize(('mode', 'value', 'expected'), [('amount', '0.13', '7.44'), ('percent', '10', '6.81'), ('final', '3.65', '3.65')])
def test_quantity_change_retains_method_and_plan_confirm_keeps_exact_total(client, mode, value, expected):
    plan = create(client, line(discount_mode=mode, discount_value=value), plan=True)
    stale = client.patch(f"/api/v1/plans/{plan['id']}", json={'receipt_items': [
        {key: value for key, value in line().items() if key not in ('discount_mode', 'discount_value')}
    ]})
    assert stale.status_code == 400, stale.text
    row = plan['receipt_items'][0] | {'quantity': '0.484'}
    updated = client.patch(f"/api/v1/plans/{plan['id']}", json={'receipt_items': [row], 'amount': None})
    assert updated.status_code == 200, updated.text
    assert_total(updated.json(), expected, '7.57')
    confirmed = client.post(f"/api/v1/plans/{plan['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert_total(confirmed.json()['operation'], expected, '7.57')


def test_final_without_known_regular_price_and_small_effective_price(client):
    purchase = create(client, line(quantity='100', unit_price='0.0001', regular_unit_price=None,
                                   discount_mode='final', discount_value='0.01'))
    row = assert_total(purchase, '0.01', None)
    assert Decimal(row['unit_price']) == Decimal('0.0001')
    updated = client.patch(f"/api/v1/operations/{purchase['id']}", json={'receipt_items': [row], 'amount': None})
    assert updated.status_code == 200, updated.text
    assert_total(updated.json(), '0.01', None)


def test_stale_client_cannot_erase_exact_total_but_explicit_removal_works(client):
    purchase = create(client, line())
    row = purchase['receipt_items'][0]
    stale = {key: value for key, value in row.items() if key not in ('discount_mode', 'discount_value')}
    response = client.patch(f"/api/v1/operations/{purchase['id']}", json={'receipt_items': [stale]})
    assert response.status_code == 400, response.text
    response = client.patch(f"/api/v1/operations/{purchase['id']}", json={'note': 'Без изменений в чеке'})
    assert_total(response.json(), '3.65')
    cleared = row | dict(is_discounted=False, discount_mode=None, discount_value=None, unit_price='15.64')
    response = client.patch(f"/api/v1/operations/{purchase['id']}", json={'receipt_items': [cleared], 'amount': None})
    assert response.status_code == 200, response.text
    assert_total(response.json(), '3.78', None)


@pytest.mark.parametrize('invalid', [
    {'discount_value': '-1'}, {'discount_value': '0.001'}, {'discount_value': '4'},
    {'discount_mode': 'percent', 'discount_value': '100'},
    {'discount_mode': 'percent', 'discount_value': '1.00001'},
    {'discount_mode': 'final', 'discount_value': '0'},
    {'discount_mode': 'final', 'discount_value': '3.79'},
    {'regular_unit_price': None}, {'is_discounted': False},
    {'discount_mode': None}, {'discount_value': None},
    {'discount_mode': 'final', 'discount_value': 'NaN'},
])
def test_invalid_calculation_rejected_without_creating_operations(client, invalid):
    response = client.post('/api/v1/operations', json={'kind': 'expense', 'operation_date': '2026-10-12', 'receipt_items': [line(**invalid)]})
    assert response.status_code in (400, 422), response.text
    assert client.get('/api/v1/operations').json()['total'] == 0


def test_percent_rounds_discount_half_up_from_rounded_subtotal(client):
    result = create(client, line(quantity='1', regular_unit_price='0.15', unit_price='0.15', discount_mode='percent', discount_value='10'))
    assert_total(result, '0.13', '0.15')
