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


@pytest.mark.parametrize('unknown_target', [False, True])
@pytest.mark.parametrize('mapped', [False, True])
@pytest.mark.parametrize('known', [dict(sale_unit='kg'), PACK])
def test_merge_missing_defaults_preserves_offer_units_prices_and_receipts(client, unknown_target, mapped, known):
    from app.main import app
    from app.db.session import get_db
    from app.db.models import CatalogProduct

    unknown = product(client)
    measured = product(client, **known)
    old = operation(client, [line(product_id=unknown['id'], shop_name='Green', **(known if mapped else {}))])
    other = operation(client, [line(product_id=measured['id'], shop_name='Маяк', **known)])
    offer_id = old['receipt_items'][0]['template_id']
    if mapped:
        r = client.post(f"/api/v1/operations/catalog-products/{unknown['id']}/variants", json={
            'name': 'Фасовка магазина', **known, 'codes': ['4006381333931'], 'is_archived': False,
        })
        assert r.status_code == 201, r.text
        variant_id = r.json()['variants'][0]['id']
        r = client.put(f"/api/v1/operations/catalog-products/{unknown['id']}/offers/{offer_id}/identity", json={
            'variant_id': variant_id, 'retailer_code': '1459548',
        })
        assert r.status_code == 200, r.text
    # Reproduce legacy catalog data: the source has an explicit measurement,
    # while the product default was never populated.
    session = app.dependency_overrides[get_db]()
    db = next(session)
    try:
        row = db.get(CatalogProduct, unknown['id'])
        for field in FIELDS:
            setattr(row, field, None)
        db.commit()
    finally:
        session.close()
    target, source = (unknown, measured) if unknown_target else (measured, unknown)
    prices_before = client.get(f'/api/v1/operations/item-templates/{offer_id}/prices').json()
    candidates = client.get('/api/v1/operations/catalog-products/merge-candidates').json()
    assert any({p['id'] for p in group['products']} == {unknown['id'], measured['id']} for group in candidates['items'])
    r = client.post(f"/api/v1/operations/catalog-products/{target['id']}/merge", json={'source_product_ids': [source['id']]})
    assert r.status_code == 200, r.text
    merged = r.json()['product']
    assert merged['sale_unit'] == known['sale_unit']
    assert merged['offers_count'] == 2
    original_offer = next(o for o in merged['offers'] if o['id'] == offer_id)
    assert original_offer['sale_unit'] == (known['sale_unit'] if mapped else None)
    assert client.get(f'/api/v1/operations/item-templates/{offer_id}/prices').json() == prices_before
    if mapped:
        identity = client.get(f"/api/v1/operations/catalog-products/{target['id']}/identity").json()
        mapping = next(m for m in identity['offers'] if m['template_id'] == offer_id)
        assert mapping['variant_id'] == variant_id and mapping['retailer_code'] == '1459548'
        assert next(v for v in identity['variants'] if v['id'] == variant_id)['codes'] == ['4006381333931']
    for purchase in [old, other]:
        saved = client.get(f"/api/v1/operations/{purchase['id']}").json()
        assert saved['amount'] == purchase['amount']
        for field in (*FIELDS, 'quantity', 'unit_price', 'line_total', 'variant_snapshot'):
            assert saved['receipt_items'][0].get(field) == purchase['receipt_items'][0].get(field)


@pytest.mark.parametrize('measurements', [
    [dict(sale_unit='kg'), dict(sale_unit='piece')],
    [PACK, {**PACK, 'package_quantity': '800'}],
])
def test_empty_target_cannot_bridge_conflicting_sources(client, measurements):
    unknown = product(client)
    sources = [product(client, **m) for m in measurements]
    response = client.post(f"/api/v1/operations/catalog-products/{unknown['id']}/merge", json={
        'source_product_ids': [p['id'] for p in sources],
    })
    assert response.status_code == 400, response.text
    assert all(client.get(f"/api/v1/operations/catalog-products/{p['id']}").status_code == 200 for p in [unknown, *sources])


def test_missing_default_does_not_hide_conflicting_source_variant(client):
    from tests.api.test_catalog_products_api import _source, _offer
    unknown = product(client)
    weighted = product(client, sale_unit='kg')
    offer = _offer(client, source_id=_source(client, 'Green'), name='Крупа', price='3.25', product_id=unknown['id'])
    r = client.post(f"/api/v1/operations/catalog-products/{unknown['id']}/variants", json={
        'name': 'Упаковка', **PACK, 'codes': [], 'is_archived': False,
    })
    variant_id = r.json()['variants'][0]['id']
    assert client.put(f"/api/v1/operations/catalog-products/{unknown['id']}/offers/{offer['id']}/identity", json={'variant_id': variant_id}).status_code == 200
    r = client.post(f"/api/v1/operations/catalog-products/{weighted['id']}/merge", json={'source_product_ids': [unknown['id']]})
    assert r.status_code == 400, r.text


def test_merge_keeps_site_tracking_and_history_without_replaying_suppressed_alerts(client):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.main import app
    from app.db.session import get_db
    from app.db.models.catalog_watch import CatalogWatch, CatalogOfferWatch, CatalogPriceEvent
    from tests.api.test_catalog_products_api import _source, _offer

    target = product(client, sale_unit='kg')
    source = product(client)
    target_offer = _offer(client, source_id=_source(client, 'Маяк'), name='Крупа', price='18.59', product_id=target['id'])
    source_offer = _offer(client, source_id=_source(client, 'Green'), name='Крупа', price='19.39', product_id=source['id'])
    now = datetime.now(timezone.utc)
    session = app.dependency_overrides[get_db]()
    db = next(session)
    try:
        db.add(CatalogWatch(user_id=1, product_id=source['id'], enabled=True, enabled_at=now-timedelta(days=1)))
        db.add(CatalogWatch(user_id=1, product_id=target['id'], enabled=False, enabled_at=now-timedelta(days=2)))
        db.add(CatalogOfferWatch(user_id=1, product_id=source['id'], template_id=source_offer['id'],
            url='https://green-dostavka.by/product/test', snapshot={'price': '19.39'}, checked_at=now, next_check_at=now))
        for product_id, offer_id, offset, sent in [
            (source['id'], source_offer['id'], 0, None),
            (source['id'], source_offer['id'], -3, None),
            (source['id'], source_offer['id'], -2, now),
            (target['id'], target_offer['id'], 0, None),
        ]:
            db.add(CatalogPriceEvent(user_id=1, product_id=product_id, template_id=offer_id,
                data={'price': '19.39', 'offset': offset}, created_at=now+timedelta(days=offset), telegram_sent_at=sent))
        db.commit()
        before = [(e.id, e.data, e.created_at, e.template_id) for e in db.scalars(select(CatalogPriceEvent).order_by(CatalogPriceEvent.id))]
        r = client.post(f"/api/v1/operations/catalog-products/{target['id']}/merge", json={'source_product_ids': [source['id']]})
        assert r.status_code == 200, r.text
        db.expire_all()
        watch = db.get(CatalogOfferWatch, source_offer['id'])
        assert watch.product_id == target['id'] and watch.snapshot == {'price': '19.39'}
        assert db.get(CatalogWatch, target['id']).enabled
        events = list(db.scalars(select(CatalogPriceEvent).order_by(CatalogPriceEvent.id)))
        assert [(e.id, e.data, e.created_at, e.template_id) for e in events] == before
        assert all(e.product_id == target['id'] for e in events)
        assert [e.telegram_sent_at is None for e in events] == [True, False, False, False]
    finally:
        session.close()
