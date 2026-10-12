from app.api.deps import get_current_user_id
from app.main import app
from tests.api.test_catalog_product_linkage_api import client, _source, _operation

CODE='4006381333931'


def product(client,name='Молоко'):
    r=client.post('/api/v1/operations/catalog-products',json={'name':name})
    assert r.status_code==201,r.text
    return r.json()['id']


def variant(client,p,**extra):
    return client.post(f'/api/v1/operations/catalog-products/{p}/variants',json={'name':'900 мл','sale_unit':'pack','package_quantity':'900','package_unit':'ml','codes':[CODE],**extra})


def get(client,p):
    r=client.get(f'/api/v1/operations/catalog-products/{p}/identity')
    assert r.status_code==200,r.text
    return r.json()


def test_codes_leading_zeros_canonical_uniqueness_and_validation(client):
    p=product(client)
    r=variant(client,p,codes=[CODE,'0'+CODE])
    assert r.status_code==201,r.text
    assert r.json()['variants'][0]['codes']==[CODE]
    second=product(client,'Другое молоко')
    assert variant(client,second,codes=['0'+CODE]).status_code==400
    for code in ['4006381333932','1234','１２３４５６７８','00000000']:
        assert variant(client,p,codes=[code]).status_code==400
    row=get(client,p)['variants'][0]
    v=row['id']
    r=client.put(f'/api/v1/operations/catalog-products/{p}/variants/{v}',json={**row,'codes':['0'+CODE],'is_archived':True})
    assert r.status_code==200,r.text
    assert r.json()['variants'][0]['codes']==['0'+CODE]
    assert variant(client,second).status_code==400  # Archived codes stay reserved.
    assert len(get(client,p)['variants'])==1


def test_offer_scope_safe_urls_and_receipts_unchanged(client):
    p=product(client); s=_source(client,'Green')
    op=_operation(client,product_id=p,source_id=s,name='Молоко',price='3',operation_date='2026-10-01')
    offer=op['receipt_items'][0]['template_id']
    r=variant(client,p);assert r.status_code==201,r.text
    v=r.json()['variants'][0]['id']
    endpoint=f'/api/v1/operations/catalog-products/{p}/offers/{offer}/identity'
    data={'variant_id':v,'retailer_code':'000-42','external_name':'МОЛ.900МЛ','product_url':'https://example.com/item/42'}
    assert client.put(endpoint,json=data).status_code==200
    assert get(client,p)['offers'][0]['retailer_code']=='000-42'
    assert client.get(f"/api/v1/operations/{op['id']}").json()==op
    for url in ['javascript:alert(1)','file:///etc/passwd','https://user:secret@example.com']:
        assert client.put(endpoint,json={**data,'product_url':url}).status_code==422
    other=product(client,'Другое')
    other_v=variant(client,other,codes=[]).json()['variants'][0]['id']
    assert client.put(endpoint,json={**data,'variant_id':other_v}).status_code==400
    assert client.put(f'/api/v1/operations/catalog-products/{other}/offers/{offer}/identity',json=data).status_code==404
    app.dependency_overrides[get_current_user_id]=lambda:2
    assert client.get(f'/api/v1/operations/catalog-products/{p}/identity').status_code==404
    assert client.put(endpoint,json=data).status_code==404
    assert variant(client,p).status_code==404


def test_catalog_search_by_barcode_and_retailer_code_is_opt_in(client):
    p=product(client);s=_source(client,'Green')
    op=_operation(client,product_id=p,source_id=s,name='Молоко',price='3',operation_date='2026-10-01')
    offer=op['receipt_items'][0]['template_id']
    assert variant(client,p).status_code==201
    assert client.put(f'/api/v1/operations/catalog-products/{p}/offers/{offer}/identity',json={'retailer_code':'000-42'}).status_code==200
    for q in [CODE,'0'+CODE,'000-42']:
        r=client.get('/api/v1/operations/catalog-products',params={'q':q,'include_identifiers':True})
        assert r.status_code==200,r.text
        assert [item['id'] for item in r.json()['items']]==[p]
        assert client.get('/api/v1/operations/catalog-products',params={'q':q}).json()['total']==0
    app.dependency_overrides[get_current_user_id]=lambda:2
    assert client.get('/api/v1/operations/catalog-products',params={'q':CODE,'include_identifiers':True}).json()['total']==0


def test_merge_preserves_codes_and_detach_clears_only_variant_mapping(client):
    p=product(client);other=product(client,'Другое молоко');s=_source(client,'Green')
    op=_operation(client,product_id=p,source_id=s,name='Молоко',price='3',operation_date='2026-10-01')
    offer=op['receipt_items'][0]['template_id'];v=variant(client,p).json()['variants'][0]['id']
    assert client.put(f'/api/v1/operations/catalog-products/{p}/offers/{offer}/identity',json={'variant_id':v,'retailer_code':'ABC'}).status_code==200
    r=client.post(f'/api/v1/operations/catalog-products/{other}/merge',json={'source_product_ids':[p]})
    assert r.status_code==200,r.text
    assert get(client,other)['variants'][0]['id']==v
    assert get(client,other)['offers'][0]['variant_id']==v
    r=client.post(f'/api/v1/operations/catalog-products/{other}/offers/{offer}/detach',json={})
    assert r.status_code==200,r.text
    dest=r.json()['product']['id'] if 'product' in r.json() else r.json()['id']
    assert get(client,dest)['offers'][0]['variant_id'] is None
    assert get(client,dest)['offers'][0]['retailer_code']=='ABC'
    assert get(client,other)['variants'][0]['codes']==[CODE]


def test_archive_variant_keeps_mapping_but_rejects_new_assignments(client):
    p=product(client);r=variant(client,p);row=r.json()['variants'][0]
    assert client.put(f"/api/v1/operations/catalog-products/{p}/variants/{row['id']}",json={**row,'is_archived':True}).status_code==200
    op=_operation(client,product_id=p,source_id=_source(client,'Green'),name='Молоко',price='3',operation_date='2026-10-01')
    offer=op['receipt_items'][0]['template_id']
    assert client.put(f'/api/v1/operations/catalog-products/{p}/offers/{offer}/identity',json={'variant_id':row['id']}).status_code==400
    r=client.put(f"/api/v1/operations/catalog-products/{p}/variants/{row['id']}",json={**row,'is_archived':False})
    assert r.status_code==200
    assert client.put(f'/api/v1/operations/catalog-products/{p}/offers/{offer}/identity',json={'variant_id':row['id']}).status_code==200
