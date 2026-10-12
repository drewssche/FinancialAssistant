from decimal import Decimal

from app.api.deps import get_current_user_id
from app.main import app
from tests.api.test_catalog_product_linkage_api import client
from tests.api.test_catalog_identity_api import product, variant, CODE

PACK = dict(sale_unit='pack', package_quantity='900', package_unit='ml')


def setup_variant(client):
    p = product(client)
    result = variant(client, p, codes=['0' + CODE])
    assert result.status_code == 201, result.text
    return p, result.json()['variants'][0]


def line(p, v, **extra):
    return dict(name='Молоко', product_id=p, variant_id=v['id'], **PACK,
                quantity='2', unit_price='3.25', **extra)


def create(client, items, *, plan=False):
    payload = {'kind': 'expense', 'receipt_items': items,
               'scheduled_date' if plan else 'operation_date': '2026-10-13'}
    response = client.post('/api/v1/plans' if plan else '/api/v1/operations', json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_snapshot_survives_catalog_change_edit_delete_restore_and_merge(client):
    p, v = setup_variant(client)
    purchase = create(client, [line(p, v)])
    row = purchase['receipt_items'][0]
    snapshot = dict(variant_id=v['id'], name='900 мл', codes=['0' + CODE])
    assert row['variant_snapshot'] == snapshot
    assert Decimal(purchase['amount']) == Decimal('6.50')
    changed = client.put(f"/api/v1/operations/catalog-products/{p}/variants/{v['id']}", json={
        **v, 'name': '800 мл', 'package_quantity': '800', 'codes': [], 'is_archived': True})
    assert changed.status_code == 200, changed.text
    target = product(client, 'Общий товар')
    assert client.post(f'/api/v1/operations/catalog-products/{target}/merge', json={'source_product_ids': [p]}).status_code == 200
    current = client.get(f"/api/v1/operations/{purchase['id']}").json()['receipt_items'][0]
    assert current['variant_snapshot'] == snapshot
    assert Decimal(current['package_quantity']) == 900
    updated = client.patch(f"/api/v1/operations/{purchase['id']}", json={'amount': '9.75', 'receipt_items': [{**current, 'quantity': '3'}]})
    assert updated.status_code == 200, updated.text
    assert updated.json()['receipt_items'][0]['variant_snapshot'] == snapshot
    assert Decimal(updated.json()['amount']) == Decimal('9.75')
    assert client.delete(f"/api/v1/operations/{purchase['id']}").status_code == 204
    restored = client.post(f"/api/v1/operations/{purchase['id']}/restore")
    assert restored.status_code == 200, restored.text
    assert restored.json()['receipt_items'][0]['variant_snapshot'] == snapshot


def test_plan_edit_and_confirmation_preserve_archived_snapshot(client):
    p, v = setup_variant(client)
    plan = create(client, [line(p, v)], plan=True)
    snapshot = plan['receipt_items'][0]['variant_snapshot']
    assert client.put(f"/api/v1/operations/catalog-products/{p}/variants/{v['id']}", json={**v, 'is_archived': True}).status_code == 200
    row = plan['receipt_items'][0]
    stale = {key: val for key, val in row.items() if key != 'variant_snapshot'}
    assert client.patch(f"/api/v1/plans/{plan['id']}", json={'receipt_items': [stale]}).status_code == 400
    response = client.patch(f"/api/v1/plans/{plan['id']}", json={'amount': '9.75', 'receipt_items': [{**row, 'quantity': '3'}]})
    assert response.status_code == 200, response.text
    assert response.json()['receipt_items'][0]['variant_snapshot'] == snapshot
    confirmed = client.post(f"/api/v1/plans/{plan['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()['operation']['receipt_items'][0]['variant_snapshot'] == snapshot
    assert Decimal(confirmed.json()['operation']['amount']) == Decimal('9.75')


def test_new_selection_requires_owned_active_variant_matching_product_and_dimensions(client):
    p, v = setup_variant(client)
    other = product(client, 'Другой товар')
    for item in [line(other, v), {**line(p, v), 'package_quantity': '800'}]:
        result = client.post('/api/v1/operations', json={'kind': 'expense', 'operation_date': '2026-10-13', 'receipt_items': [item]})
        assert result.status_code == 400, result.text
    assert client.get('/api/v1/operations').json()['total'] == 0
    assert client.put(f"/api/v1/operations/catalog-products/{p}/variants/{v['id']}", json={**v, 'is_archived': True}).status_code == 200
    result = client.post('/api/v1/plans', json={'kind': 'expense', 'scheduled_date': '2026-10-13', 'receipt_items': [line(p, v)]})
    assert result.status_code == 400, result.text
    app.dependency_overrides[get_current_user_id] = lambda: 2
    own = product(client, 'Свой товар')
    result = client.post('/api/v1/operations', json={'kind': 'expense', 'operation_date': '2026-10-13', 'receipt_items': [line(own, v)]})
    assert result.status_code == 400, result.text
    assert client.get('/api/v1/operations').json()['total'] == 0


def test_explicit_manual_clear_and_legacy_client_guard(client):
    p, v = setup_variant(client)
    purchase = create(client, [line(p, v)])
    row = purchase['receipt_items'][0]
    stale = {key: value for key, value in row.items() if key != 'variant_snapshot'}
    response = client.patch(f"/api/v1/operations/{purchase['id']}", json={'receipt_items': [stale]})
    assert response.status_code == 400, response.text
    assert client.get(f"/api/v1/operations/{purchase['id']}").json()['receipt_items'][0]['variant_snapshot'] == row['variant_snapshot']
    cleared = client.patch(f"/api/v1/operations/{purchase['id']}", json={'receipt_items': [{**row, 'variant_snapshot': None, 'package_quantity': '800'}]})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()['receipt_items'][0]['variant_snapshot'] is None
    assert Decimal(cleared.json()['amount']) == Decimal('6.50')
    # Ordinary legacy clients can still add receipts without any package selection.
    legacy = create(client, [dict(name='Молоко', product_id=p, quantity='1', unit_price='3.25')])
    assert legacy['receipt_items'][0]['variant_snapshot'] is None
    assert legacy['receipt_items'][0]['package_quantity'] is None


def test_two_variants_of_same_product_in_one_discounted_receipt(client):
    p, v = setup_variant(client)
    small = variant(client, p, name='500 мл', package_quantity='500', codes=[]).json()['variants'][-1]
    receipt = create(client, [line(p, v), {**line(p, small), 'package_quantity': '500',
        'is_discounted': True, 'discount_mode': 'final', 'discount_value': '4.00', 'regular_unit_price': '3.25'}])
    rows = receipt['receipt_items']
    assert [row['variant_snapshot']['variant_id'] for row in rows] == [v['id'], small['id']]
    assert [Decimal(row['package_quantity']) for row in rows] == [900, 500]
    assert Decimal(receipt['amount']) == Decimal('10.50')


def test_activity_detects_variant_change_on_first_of_two_identical_offer_lines():
    from app.services.activity_service import ActivityService
    before = [dict(template_id=1, name='Молоко', quantity='1', unit_price='3'),
              dict(template_id=1, name='Молоко', quantity='1', unit_price='3')]
    after = [{**before[0], 'variant_snapshot': dict(variant_id=1, name='900 мл', codes=[])}, before[1]]
    changes = ActivityService.summarize_receipt_changes(before, after)
    assert changes['changed_count'] == 1
    assert changes['added_count'] == changes['removed_count'] == 0
    assert ActivityService.summarize_receipt_changes(after, after)['changed_count'] == 0
