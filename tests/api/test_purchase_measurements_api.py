from decimal import Decimal

import pytest

from tests.api.test_catalog_products_api import client  # noqa: F401

FIELDS = ('sale_unit', 'package_quantity', 'package_unit')
PACK = dict(sale_unit='pack', package_quantity='900', package_unit='g')


def product(client, **extra):
    response = client.post('/api/v1/operations/catalog-products', json={'name': 'Крупа', **extra})
    assert response.status_code == 201, response.text
    return response.json()


def line(**extra):
    return dict(name='Крупа', quantity='2', unit_price='3.25', **extra)


def operation(client, items):
    response = client.post('/api/v1/operations', json={
        'kind': 'expense', 'operation_date': '2026-10-12', 'receipt_items': items,
    })
    assert response.status_code == 201, response.text
    return response.json()


def assert_pack(row, quantity='900'):
    assert row['sale_unit'] == 'pack'
    assert Decimal(row['package_quantity']) == Decimal(quantity)
    assert row['package_unit'] == 'g'


def test_measurements_are_explicit_and_legacy_amounts_unchanged(client):
    legacy = product(client)
    assert all(legacy[key] is None for key in FIELDS)
    measured = product(client, **PACK)
    purchase = operation(client, [line(product_id=measured['id'])])
    assert Decimal(purchase['amount']) == Decimal('6.50')
    assert all(purchase['receipt_items'][0][key] is None for key in FIELDS)
    # Unrelated product PATCH does not erase its defaults.
    patched = client.patch(f"/api/v1/operations/catalog-products/{measured['id']}", json={'name': 'Крупа новая'})
    assert patched.status_code == 200, patched.text
    assert_pack(patched.json())


def test_purchase_snapshot_survives_product_change_edit_and_delete_restore(client):
    item = product(client, **PACK)
    purchase = operation(client, [line(product_id=item['id'], **PACK), line(product_id=item['id'], **{**PACK, 'package_quantity': '800'})])
    assert Decimal(purchase['amount']) == Decimal('13.00')
    response = client.patch(f"/api/v1/operations/catalog-products/{item['id']}", json={'package_quantity': '700'})
    assert response.status_code == 200, response.text
    response = client.patch(f"/api/v1/operations/{purchase['id']}", json={'note': 'Старая фасовка'})
    assert response.status_code == 200, response.text
    assert_pack(response.json()['receipt_items'][0])
    assert_pack(response.json()['receipt_items'][1], '800')
    # Stale browser clients must not silently clear measurement snapshots.
    rejected = client.patch(f"/api/v1/operations/{purchase['id']}", json={'receipt_items': [line(product_id=item['id'])]})
    assert rejected.status_code == 400, rejected.text
    updated = client.patch(f"/api/v1/operations/{purchase['id']}", json={'receipt_items': [line(product_id=item['id'], **PACK)]})
    assert updated.status_code == 200, updated.text
    assert_pack(updated.json()['receipt_items'][0])
    assert client.delete(f"/api/v1/operations/{purchase['id']}").status_code == 204
    restored = client.post(f"/api/v1/operations/{purchase['id']}/restore")
    assert restored.status_code == 200, restored.text
    assert_pack(restored.json()['receipt_items'][0])
    assert Decimal(restored.json()['amount']) == Decimal(updated.json()['amount'])


def test_plan_confirmation_uses_its_snapshot_and_weighted_goods_keep_totals(client):
    item = product(client, **PACK)
    response = client.post('/api/v1/plans', json={
        'kind': 'expense', 'scheduled_date': '2026-10-12',
        'receipt_items': [line(product_id=item['id'], **PACK), {
            'name': 'Сыр весовой', 'quantity': '0.242', 'unit_price': '15.64', 'sale_unit': 'kg',
        }],
    })
    assert response.status_code == 201, response.text
    plan = response.json()
    assert_pack(plan['receipt_items'][0])
    response = client.patch(f"/api/v1/operations/catalog-products/{item['id']}", json={'package_quantity': '500'})
    assert response.status_code == 200
    rejected = client.patch(f"/api/v1/plans/{plan['id']}", json={'receipt_items': [line()]})
    assert rejected.status_code == 400, rejected.text
    confirmed = client.post(f"/api/v1/plans/{plan['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    purchase = confirmed.json()['operation']
    assert_pack(purchase['receipt_items'][0])
    assert purchase['receipt_items'][1]['sale_unit'] == 'kg'
    assert purchase['receipt_items'][1]['package_quantity'] is None
    assert Decimal(purchase['receipt_items'][1]['line_total']) == Decimal('3.78')
    assert Decimal(purchase['amount']) == Decimal('10.28')


@pytest.mark.parametrize('bad', [
    {'sale_unit': 'ton'}, {'sale_unit': 'kg', 'package_quantity': '900', 'package_unit': 'g'},
    {'package_quantity': '900', 'package_unit': 'g'}, {'sale_unit': 'pack', 'package_unit': 'g'},
    {'sale_unit': 'pack', 'package_quantity': '900'}, {**PACK, 'package_quantity': '-1'},
    {**PACK, 'package_quantity': '0.0001'}, {**PACK, 'package_quantity': 'NaN'},
])
def test_invalid_measurements_are_rejected_atomically(client, bad):
    response = client.post('/api/v1/operations/catalog-products', json={'name': 'Неверный', **bad})
    assert response.status_code in (400, 422), response.text
    response = client.post('/api/v1/operations', json={
        'kind': 'expense', 'operation_date': '2026-10-12', 'receipt_items': [line(**bad)],
    })
    assert response.status_code in (400, 422), response.text
    assert client.get('/api/v1/operations/catalog-products').json()['total'] == 0
    assert client.get('/api/v1/operations').json()['total'] == 0


def test_merge_does_not_replace_a_different_package_default(client):
    first = product(client, **PACK)
    second = product(client, **{**PACK, 'package_quantity': '800'})
    response = client.post(f"/api/v1/operations/catalog-products/{first['id']}/merge", json={'source_product_ids': [second['id']]})
    assert response.status_code == 400, response.text
    assert_pack(client.get(f"/api/v1/operations/catalog-products/{first['id']}").json())
    assert_pack(client.get(f"/api/v1/operations/catalog-products/{second['id']}").json(), '800')


def test_new_weighted_product_defaults_and_historical_snapshot(client):
    purchase = operation(client, [dict(name='Колбаса Рубленая', shop_name='Green', quantity='0.530', unit_price='18.69', sale_unit='kg')])
    row = purchase['receipt_items'][0]
    assert Decimal(row['line_total']) == Decimal('9.91')
    catalog = client.get(f"/api/v1/operations/catalog-products/{row['product_id']}").json()
    assert catalog['sale_unit'] == 'kg'
    assert catalog['package_quantity'] is None
    changed = client.patch(f"/api/v1/operations/catalog-products/{row['product_id']}", json={
        'name': 'Колбаса', 'sale_unit': 'piece', 'package_quantity': '1', 'package_unit': 'kg',
    })
    assert changed.status_code == 200, changed.text
    saved = client.get(f"/api/v1/operations/{purchase['id']}").json()['receipt_items'][0]
    assert saved['sale_unit'] == 'kg' and saved['name'] == 'Колбаса Рубленая'
    assert Decimal(saved['line_total']) == Decimal('9.91')
    # A later purchase with explicit units must not overwrite existing catalog defaults.
    operation(client, [dict(name='Колбаса Рубленая', shop_name='Green', quantity='0.2', unit_price='18.69', sale_unit='kg')])
    assert client.get(f"/api/v1/operations/catalog-products/{row['product_id']}").json()['sale_unit'] == 'piece'


def test_conflicting_new_product_sizes_do_not_pick_arbitrary_default(client):
    purchase = operation(client, [line(**PACK), line(**{**PACK, 'package_quantity': '800'})])
    row = purchase['receipt_items'][0]
    catalog = client.get(f"/api/v1/operations/catalog-products/{row['product_id']}").json()
    assert all(catalog[key] is None for key in FIELDS)
    assert_pack(row)
    assert_pack(purchase['receipt_items'][1], '800')


def test_new_plan_product_inherits_explicit_unit(client):
    response = client.post('/api/v1/plans', json={
        'kind': 'expense', 'scheduled_date': '2026-10-16',
        'receipt_items': [dict(name='Бекон', quantity='0.53', unit_price='18.69', sale_unit='kg')],
    })
    assert response.status_code == 201, response.text
    row = response.json()['receipt_items'][0]
    assert client.get(f"/api/v1/operations/catalog-products/{row['product_id']}").json()['sale_unit'] == 'kg'


@pytest.mark.parametrize('target_unit,source_unit', [('piece','pack'),('pack','piece')])
@pytest.mark.parametrize('own_variant', [False, True, 'archived'])
def test_merge_piece_and_pack_keeps_offer_measurements_codes_and_history(client,target_unit,source_unit,own_variant):
    target=product(client,**{**PACK,'sale_unit':target_unit})
    source=product(client,**{**PACK,'sale_unit':source_unit})
    purchase=operation(client,[line(product_id=source['id'],shop_name='Green',**{**PACK,'sale_unit':source_unit})])
    offer=purchase['receipt_items'][0]['template_id']
    variant_id=None
    if own_variant:
        r=client.post(f"/api/v1/operations/catalog-products/{source['id']}/variants",json={
            'name':'Размер источника','sale_unit':source_unit,'package_quantity':'800','package_unit':'g','codes':['4006381333931'],'is_archived':False})
        assert r.status_code==201,r.text
        variant_id=r.json()['variants'][0]['id']
    r=client.put(f"/api/v1/operations/catalog-products/{source['id']}/offers/{offer}/identity",json={
        'variant_id':variant_id,'retailer_code':'000-42','product_url':'https://green-dostavka.by/product/test','external_name':'Крупа магазина'})
    assert r.status_code==200,r.text
    if own_variant=='archived':
        r=client.put(f"/api/v1/operations/catalog-products/{source['id']}/variants/{variant_id}",json={
            'name':'Размер источника','sale_unit':source_unit,'package_quantity':'800','package_unit':'g','codes':['4006381333931'],'is_archived':True})
        assert r.status_code==200,r.text
    r=client.post(f"/api/v1/operations/catalog-products/{target['id']}/merge",json={'source_product_ids':[source['id']]})
    assert r.status_code==200,r.text
    merged=client.get(f"/api/v1/operations/catalog-products/{target['id']}").json()
    assert merged['sale_unit']==target_unit
    merged_offer=next(o for o in merged['offers'] if o['id']==offer)
    assert merged_offer['sale_unit']==source_unit
    identity=client.get(f"/api/v1/operations/catalog-products/{target['id']}/identity").json()
    mapping=next(m for m in identity['offers'] if m['template_id']==offer)
    assert mapping['retailer_code']=='000-42' and mapping['product_url']=='https://green-dostavka.by/product/test'
    v=next(v for v in identity['variants'] if v['id']==mapping['variant_id'])
    assert v['sale_unit']==source_unit and Decimal(v['package_quantity'])==Decimal('800' if own_variant is True else '900')
    if own_variant is True: assert v['id']==variant_id and v['codes']==['4006381333931']
    if own_variant=='archived':
        archived=next(v for v in identity['variants'] if v['id']==variant_id)
        assert archived['is_archived'] and archived['codes']==['4006381333931']
    saved=client.get(f"/api/v1/operations/{purchase['id']}").json()
    assert saved['amount']==purchase['amount']
    for key in (*FIELDS,'quantity','unit_price','line_total','variant_snapshot'):
        assert saved['receipt_items'][0].get(key)==purchase['receipt_items'][0].get(key)
