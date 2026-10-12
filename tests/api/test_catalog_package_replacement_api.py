from decimal import Decimal
from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.main import app
from tests.api.test_catalog_product_linkage_api import client, _source
from tests.api.test_catalog_identity_api import product, variant
from tests.api.test_product_price_history_api import buy


def setup(client):
    p=product(client)
    a=variant(client,p,name='1 л',package_quantity='1',package_unit='l',codes=[]).json()['variants'][-1]
    b=variant(client,p,name='900 мл',codes=[]).json()['variants'][-1]
    return p,a,b


def endpoint(p):return f'/api/v1/operations/catalog-products/{p}/package-replacements'
def confirm(client,p,a,b,**extra):
    return client.post(endpoint(p),json=dict(old_variant_id=a['id'],new_variant_id=b['id'],effective_date='2026-10-02',confirmed=True,expected_old=a,expected_new=b,**extra))
def read(client,p):
    r=client.get(endpoint(p));assert r.status_code==200,r.text
    return r.json()
def purchase(client,p,s,v,price,day,**extra):
    row={key:v[key] for key in ('sale_unit','package_quantity','package_unit')}
    row.update(variant_id=v['id']);row.update(extra.pop('row',{}))
    return buy(client,p,s,price,day,row=row,**extra)


def test_confirm_frozen_sizes_and_revoke_leave_receipts_unchanged(client):
    p,a,b=setup(client);s=_source(client,'Магазин')
    before=purchase(client,p,s,a,3,1);after=purchase(client,p,s,b,3,3)
    response=confirm(client,p,a,b);assert response.status_code==201,response.text
    item=response.json()['items'][0]
    assert item['volume_change_percent']=='-10.00'
    assert item['constant_package_price_change_percent']=='11.11'
    pair=item['comparisons'][0]
    assert pair['normalized_price_change_percent']=='11.11' and pair['package_price_change_percent']=='0.00'
    assert pair['old']['operation_id']==before['id'] and pair['new']['operation_id']==after['id']
    assert pair['regular_normalized_change_percent'] is None
    assert client.put(f"/api/v1/operations/catalog-products/{p}/variants/{b['id']}",json={**b,'name':'800 мл','package_quantity':'800','is_archived':True}).status_code==200
    frozen=read(client,p)['items'][0]
    assert frozen==item
    assert client.delete(endpoint(p)+f"/{item['id']}").status_code==200
    assert read(client,p)['items']==[]
    assert client.get(f"/api/v1/operations/{before['id']}").json()==before
    assert client.get(f"/api/v1/operations/{after['id']}").json()==after


def test_latest_before_first_after_currency_shop_and_discounts(client):
    p,a,b=setup(client);s=_source(client,'Магазин')
    purchase(client,p,s,a,2,1)
    old=purchase(client,p,s,a,3,2,row={'quantity':'2','regular_unit_price':'4','is_discounted':True,'discount_mode':'final','discount_value':'6'})
    new=purchase(client,p,s,b,3,2,row={'quantity':'2','regular_unit_price':'4','is_discounted':True,'discount_mode':'final','discount_value':'5'})
    purchase(client,p,s,b,7,4) # First after wins.
    purchase(client,p,s,a,9,4) # Old after boundary ignored.
    purchase(client,p,s,b,1,1) # New before boundary ignored.
    purchase(client,p,s,a,5,1,currency='USD',fx_rate='3') # No USD new pair.
    other=_source(client,'Другой')
    purchase(client,p,other,b,9,3) # No old at other shop.
    assert confirm(client,p,a,b).status_code==201
    comparisons=read(client,p)['items'][0]['comparisons']
    assert len(comparisons)==1
    pair=comparisons[0]
    assert pair['old']['operation_id']==old['id'] and pair['new']['operation_id']==new['id']
    assert pair['normalized_price_change_percent']=='-7.41' # Smaller pack but paid price fell.
    assert pair['regular_normalized_change_percent']=='11.11'
    assert client.delete(f"/api/v1/operations/{new['id']}").status_code==204
    assert read(client,p)['items'][0]['comparisons'][0]['new']['recorded_at']=='2026-10-04'
    assert client.post(f"/api/v1/operations/{new['id']}/restore").status_code==200
    assert read(client,p)['items'][0]['comparisons']==comparisons


def test_chain_cycles_branches_dates_stale_choices_and_dimensions(client):
    p,a,b=setup(client)
    c=variant(client,p,name='800 мл',package_quantity='800',codes=[]).json()['variants'][-1]
    assert confirm(client,p,a,b).status_code==201
    assert confirm(client,p,a,c).status_code==400
    assert confirm(client,p,c,b).status_code==400
    assert confirm(client,p,b,a).status_code==400
    payload=dict(old_variant_id=b['id'],new_variant_id=c['id'],effective_date='2026-10-01',confirmed=True,expected_old=b,expected_new=c)
    assert client.post(endpoint(p),json=payload).status_code==400
    payload['effective_date']='2026-10-03'
    assert client.post(endpoint(p),json=payload).status_code==201
    assert confirm(client,p,c,a).status_code==400
    assert confirm(client,p,a,a).status_code==400
    q,x,y=setup(client)
    assert client.put(f"/api/v1/operations/catalog-products/{q}/variants/{y['id']}",json={**y,'package_quantity':'850'}).status_code==200
    assert confirm(client,q,x,y).status_code==400
    mass=variant(client,q,name='900 г',package_unit='g',codes=[]).json()['variants'][-1]
    assert confirm(client,q,x,mass).status_code==400
    missing=variant(client,q,name='Без размера',sale_unit=None,package_quantity=None,package_unit=None,codes=[]).json()['variants'][-1]
    assert confirm(client,q,x,missing).status_code==400
    assert confirm(client,q,x,a).status_code==400


def test_owner_merge_archive_cleanup_and_no_inferred_history(client):
    p,a,b=setup(client);s=_source(client,'Магазин')
    # Dimensions without explicit historical variant identity are not proof.
    for day in (1,3):buy(client,p,s,3,day,row={'sale_unit':'pack','package_quantity':'900','package_unit':'ml'})
    response=confirm(client,p,a,b);assert response.status_code==201,response.text
    link=response.json()['items'][0];assert link['comparisons']==[]
    target=product(client,'Общее молоко')
    assert client.post(f'/api/v1/operations/catalog-products/{target}/merge',json={'source_product_ids':[p]}).status_code==200
    assert read(client,p)['items']==[] and read(client,target)['items'][0]==link
    assert client.delete(f'/api/v1/operations/catalog-products/{target}').status_code==204
    assert read(client,target)['items'][0]==link
    assert confirm(client,target,a,b).status_code==400
    app.dependency_overrides[get_current_user_id]=lambda:2
    assert client.get(endpoint(target)).status_code==404
    assert client.delete(endpoint(target)+f"/{link['id']}").status_code==404
    assert confirm(client,target,a,b).status_code==404
    app.dependency_overrides[get_current_user_id]=lambda:1
    from app.services.user_cleanup_service import hard_delete_user
    gen=app.dependency_overrides[get_db]();db=next(gen)
    try:
        assert hard_delete_user(db,user_id=1) is True
        db.commit()
    finally:gen.close()


def test_explicit_confirmation_required_and_empty_registry(client):
    p,a,b=setup(client)
    assert read(client,p)['items']==[]
    for confirmed in (False,None):
        r=client.post(endpoint(p),json={'old_variant_id':a['id'],'new_variant_id':b['id'],'effective_date':'2026-10-02','confirmed':confirmed,'expected_old':a,'expected_new':b})
        assert r.status_code==422


def test_concurrent_confirmations_serialize_on_postgres(client):
    import pytest
    from concurrent.futures import ThreadPoolExecutor
    gen=app.dependency_overrides[get_db]();db=next(gen)
    try:
        if db.get_bind().dialect.name != 'postgresql':pytest.skip('Requires PostgreSQL row locks')
    finally:gen.close()
    p,a,b=setup(client)
    c=variant(client,p,name='800 мл',package_quantity='800',codes=[]).json()['variants'][-1]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda next_variant:confirm(client,p,a,next_variant),[b,c]))
    assert sorted(r.status_code for r in responses)==[201,400]
    link=read(client,p)['items'][0]
    assert client.delete(endpoint(p)+f"/{link['id']}").status_code==200
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda args:confirm(client,p,*args),[(a,b),(b,a)]))
    assert sorted(r.status_code for r in responses)==[201,400]
    assert len(read(client,p)['items'])==1
