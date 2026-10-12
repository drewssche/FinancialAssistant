from decimal import Decimal

from app.api.deps import get_current_user_id
from app.main import app
from tests.api.test_catalog_product_linkage_api import client, _source


def setup_product(client):
    product = client.post('/api/v1/operations/catalog-products', json={'name': 'Молоко'}).json()
    source = _source(client, 'Магазин')
    return product['id'], source


def buy(client, product, source, price, day, **fields):
    row = dict(product_id=product, source_id=source, name='Молоко', quantity='1', unit_price=str(price))
    row.update(fields.pop('row', {}))
    response = client.post('/api/v1/operations', json=dict(kind='expense', operation_date=f'2026-10-{day:02}', receipt_items=[row], **fields))
    assert response.status_code == 201, response.text
    return response.json()


def history(client, product, offer, **params):
    response = client.get(f'/api/v1/operations/catalog-products/{product}/price-observations', params=dict(template_id=offer, **params))
    assert response.status_code == 200, response.text
    return response.json()


def test_repeat_price_return_edit_delete_restore_and_period(client):
    p,s = setup_product(client)
    ops = [buy(client,p,s,price,day) for day,price in enumerate([3,4,3],1)]
    offer = ops[0]['receipt_items'][0]['template_id']
    def series(**kw): return history(client,p,offer,**kw)['series'][0]
    result=series()
    assert [Decimal(r['price']) for r in result['observations']] == [3,4,3]
    assert [r['change_percent'] for r in result['observations']] == [None,'33.33','-25.00']
    assert result['change_percent']=='0.00' and result['increases']==result['decreases']==1
    assert len(series(date_from='2026-10-02')['observations'])==2
    assert series(date_from='2026-10-02')['change_percent']=='-25.00'
    response=client.patch(f"/api/v1/operations/{ops[1]['id']}",json={'operation_date':'2026-10-04'})
    assert response.status_code==200,response.text
    assert [Decimal(r['price']) for r in series()['observations']]==[3,3,4]
    assert client.delete(f"/api/v1/operations/{ops[1]['id']}").status_code==204
    assert len(series()['observations'])==2
    response=client.post(f"/api/v1/operations/{ops[1]['id']}/restore")
    assert response.status_code==200,response.text
    assert len(series()['observations'])==3
    assert len(series()['observations'])==3  # Repeated reads cannot create observations.


def test_packages_normalization_and_unknown_history_are_not_guessed(client):
    p,s=setup_product(client)
    a=buy(client,p,s,3,1,row={'sale_unit':'pack','package_quantity':'1000','package_unit':'ml'})
    buy(client,p,s,3,2,row={'sale_unit':'pack','package_quantity':'900','package_unit':'ml'})
    buy(client,p,s,8,3,row={'sale_unit':None,'package_quantity':None,'package_unit':None})
    offer=a['receipt_items'][0]['template_id']
    assert len(history(client,p,offer)['series'])==3
    normalized=history(client,p,offer,basis='normalized')
    assert normalized['excluded_count']==1
    group=normalized['series'][0]
    assert group['unit']=='l' and group['change_percent']=='11.11'
    assert group['observations'][1]['package_changed'] is True
    response=client.patch(f'/api/v1/operations/catalog-products/{p}',json={'sale_unit':'pack','package_quantity':'500','package_unit':'ml'})
    assert response.status_code==200,response.text
    assert history(client,p,offer,basis='normalized')==normalized


def test_exact_paid_price_regular_price_currency_and_free_item(client):
    p,s=setup_product(client)
    a=buy(client,p,s,10,1,row={'quantity':'0.242','sale_unit':'kg','regular_unit_price':'10','is_discounted':True,'discount_mode':'final','discount_value':'2.29'})
    offer=a['receipt_items'][0]['template_id']
    paid=history(client,p,offer,basis='normalized')['series'][0]['observations'][0]
    assert abs(Decimal(paid['price']) - Decimal('2.29')/Decimal('.242')) < Decimal('0.0000001')
    assert paid['line_total']=='2.29'
    regular=history(client,p,offer,price_kind='regular')['series'][0]
    assert Decimal(regular['observations'][0]['price'])==10
    buy(client,p,s,4,2,currency='USD',fx_rate='3.0',row={'sale_unit':'kg'})
    assert {g['currency'] for g in history(client,p,offer)['series']}=={'BYN','USD'}
    assert history(client,p,offer,price_kind='regular')['excluded_count']==1
    zero=buy(client,p,s,2,3,row={'sale_unit':'kg'})
    # Legacy/imported zero is tolerated on read; current input validation rejects it.
    from app.db.models import OperationReceiptItem
    from app.db.session import get_db
    gen=app.dependency_overrides[get_db](); db=next(gen)
    try:
        db.get(OperationReceiptItem,zero['receipt_items'][0]['id']).line_total=0
        db.commit()
    finally:
        gen.close()
    buy(client,p,s,2,4,row={'sale_unit':'kg'})
    byn=next(g for g in history(client,p,offer)['series'] if g['currency']=='BYN')
    assert byn['observations'][-1]['change_percent'] is None
    assert byn['observations'][-1]['direction']==1


def test_ownership_validation_and_plans_excluded(client):
    p,s=setup_product(client)
    a=buy(client,p,s,3,1)
    offer=a['receipt_items'][0]['template_id']
    endpoint=f'/api/v1/operations/catalog-products/{p}/price-observations'
    assert client.get(endpoint,params={'template_id':offer,'basis':'garbage'}).status_code==422
    assert client.get(endpoint,params={'template_id':offer,'date_from':'2026-10-02','date_to':'2026-10-01'}).status_code==422
    assert client.get(endpoint,params={'template_id':offer+100}).status_code==404
    plan=client.post('/api/v1/plans',json={'kind':'expense','amount':'10','scheduled_date':'2026-10-08','receipt_items':[{'product_id':p,'source_id':s,'name':'Молоко','quantity':'1','unit_price':'10'}]})
    assert plan.status_code==201,plan.text
    assert len(history(client,p,offer)['series'][0]['observations'])==1
    app.dependency_overrides[get_current_user_id]=lambda:2
    assert client.get(endpoint,params={'template_id':offer}).status_code==404


def test_full_history_not_limited_to_200_or_deduplicated(client):
    # Duplicate lines are real observations, not distinct price values.
    p,s=setup_product(client)
    from app.db.models import OperationReceiptItem
    from app.db.session import get_db
    a=buy(client,p,s,3,1)
    offer=a['receipt_items'][0]['template_id']
    gen=app.dependency_overrides[get_db]()
    db=next(gen)
    try:
        db.add_all([OperationReceiptItem(operation_id=a['id'],user_id=1,template_id=offer,name='Молоко',quantity=1,unit_price=3,line_total=3) for _ in range(205)])
        db.commit()
    finally:
        gen.close()
    assert sum(len(g['observations']) for g in history(client,p,offer)['series'])==206


def test_edit_receipt_replaces_observation_and_separates_shop_and_dimension(client):
    p,s=setup_product(client)
    a=buy(client,p,s,3,1,row={'sale_unit':'g','quantity':'100'})
    offer=a['receipt_items'][0]['template_id']
    endpoint=f"/api/v1/operations/{a['id']}"
    response=client.patch(endpoint,json={'receipt_items':[{'template_id':offer,'product_id':p,'source_id':s,'name':'Молоко','quantity':'1','unit_price':'5','sale_unit':'kg','package_quantity':None,'package_unit':None,'discount_mode':None,'discount_value':None}]})
    assert response.status_code==200,response.text
    group=history(client,p,offer,basis='normalized')['series'][0]
    assert len(group['observations'])==1 and Decimal(group['observations'][0]['price'])==5
    b=buy(client,p,s,6,2,row={'sale_unit':'l'})
    buy(client,p,s,7,3,row={'sale_unit':'kg'})
    from app.db.models import OperationReceiptItem
    from app.db.session import get_db
    gen=app.dependency_overrides[get_db]();db=next(gen)
    try:
        db.get(OperationReceiptItem,b['receipt_items'][0]['id']).shop_name='Другой филиал'
        db.commit()
    finally:
        gen.close()
    groups=history(client,p,offer,basis='normalized')['series']
    assert len(groups)==2 and {g['unit'] for g in groups}=={'kg','l'}
    assert next(g for g in groups if g['unit']=='kg')['change_percent']=='40.00'
