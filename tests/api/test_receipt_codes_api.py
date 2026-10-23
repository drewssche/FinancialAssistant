from app.main import app
from app.api.deps import get_current_user_id
from tests.api.test_catalog_product_linkage_api import client, _source
from tests.api.test_catalog_identity_api import product, variant, get, CODE


def lookup(client,codes,shop='Green'):
    result=client.post('/api/v1/operations/catalog-products/lookup-codes',json={'codes':codes,'shop_name':shop})
    assert result.status_code==200,result.text
    return result.json()


def receipt(client,entries,**fields):
    row={'name':'Молоко','shop_name':'Green','quantity':'2','unit_price':'3.10',
         'sale_unit':'pack','package_quantity':'900','package_unit':'ml','catalog_codes':entries,**fields}
    return client.post('/api/v1/operations',json={'kind':'expense','operation_date':'2026-10-16','receipt_items':[row]})


def test_atomic_codes_new_product_exact_lookup_and_repeat_edit(client):
    codes=[{'kind':'barcode','code':'0'+CODE},{'kind':'retailer','code':'000-42'}]
    result=receipt(client,codes)
    assert result.status_code==201,result.text
    operation=result.json();row=operation['receipt_items'][0];p=row['product_id']
    assert str(operation['receipt_total'])=='6.20'
    assert row['variant_snapshot']['codes']==['0'+CODE]
    identity=get(client,p)
    assert identity['offers'][0]['retailer_code']=='000-42'
    matched=lookup(client,[{'kind':'barcode','code':CODE},{'kind':'retailer','code':'000-42'}])
    assert matched['auto_match'] and len(matched['items'])==1
    assert matched['items'][0]['product_id']==p
    assert set(matched['items'][0]['matched_by'])=={'barcode','retailer'}
    assert matched['items'][0]['package_quantity']=='900.000'
    assert not lookup(client,[{'kind':'retailer','code':'000-42'}],'Соседи')['items']
    # Repeat an existing receipt save: append-only registration must not duplicate codes or change money.
    updated=client.patch(f"/api/v1/operations/{operation['id']}",json={'receipt_items':[{**row,'catalog_codes':codes}]})
    assert updated.status_code==200,updated.text
    assert updated.json()['receipt_total']==operation['receipt_total']
    assert len(get(client,p)['variants'])==1
    app.dependency_overrides[get_current_user_id]=lambda:2
    assert lookup(client,codes)['items']==[]


def test_conflicting_codes_roll_back_all_receipt_changes(client):
    p=product(client);assert variant(client,p).status_code==201
    before=client.get('/api/v1/operations').json()['total']
    rejected=receipt(client,[{'kind':'barcode','code':CODE},{'kind':'retailer','code':'new-sku'}],name='Другой товар')
    assert rejected.status_code==400,rejected.text
    assert client.get('/api/v1/operations').json()['total']==before
    assert lookup(client,[{'kind':'retailer','code':'new-sku'}])['items']==[]
    assert len(get(client,p)['variants'])==1
    detail=rejected.json()['detail']
    assert detail['type']=='receipt_code_conflict'
    assert detail['item_index']==0 and detail['item_name']=='Другой товар'
    assert detail['codes']==[{'kind':'barcode','code':CODE}]
    assert detail['owners'][0]['product_id']==p
    assert detail['owners'][0]['product_name']=='Молоко'


def test_conflict_reports_second_position_and_rolls_back_create_and_edit(client):
    p=product(client);assert variant(client,p).status_code==201
    original=receipt(client,[],name='Первый товар').json()
    before=client.get('/api/v1/operations').json()['total']
    rows=[{'name':'Первый товар','quantity':'1','unit_price':'1.23','shop_name':'Green'},
          {'name':'Конфликтующий товар','quantity':'4','unit_price':'1.10','shop_name':'Green',
           'catalog_codes':[{'kind':'barcode','code':CODE}]}]
    rows=[{**row,'sale_unit':None,'package_quantity':None,'package_unit':None} for row in rows]
    for method,url,payload in [('POST','/api/v1/operations',{'kind':'expense','operation_date':'2026-10-16','receipt_items':rows}),
                               ('PATCH',f"/api/v1/operations/{original['id']}",{'receipt_items':rows})]:
        result=client.request(method,url,json=payload)
        assert result.status_code==400,result.text
        detail=result.json()['detail']
        assert isinstance(detail,dict), (method,detail)
        assert detail['item_index']==1 and detail['item_name']=='Конфликтующий товар'
        assert detail['codes'][0]['code']==CODE and detail['owners'][0]['product_id']==p
        assert client.get('/api/v1/operations').json()['total']==before
        assert client.get(f"/api/v1/operations/{original['id']}").json()==original


def test_other_users_barcode_does_not_leak_owner_in_conflict(client):
    owner=product(client,'Приватный товар');assert variant(client,owner).status_code==201
    app.dependency_overrides[get_current_user_id]=lambda:2
    result=receipt(client,[{'kind':'barcode','code':CODE}],name='Мой товар')
    assert result.status_code==201,result.text
    assert 'Приватный товар' not in result.text



def test_sku_conflict_identifies_only_sku_and_owner(client):
    first=receipt(client,[{'kind':'retailer','code':'00042'}])
    assert first.status_code==201,first.text
    owner=first.json()['receipt_items'][0]['product_id']
    rejected=receipt(client,[{'kind':'barcode','code':CODE},{'kind':'retailer','code':'00042'}],name='Другой товар')
    assert rejected.status_code==400,rejected.text
    detail=rejected.json()['detail']
    assert detail['item_index']==0
    assert detail['codes']==[{'kind':'retailer','code':'00042'}]
    assert detail['owners'][0]['product_id']==owner
    # The barcode created earlier in the same transaction is rolled back too.
    assert lookup(client,[{'kind':'barcode','code':CODE}])['items']==[]


def test_sku_is_source_scoped_and_ambiguity_never_auto_matches(client):
    first=receipt(client,[{'kind':'retailer','code':'00042'}]);assert first.status_code==201,first.text
    second=receipt(client,[{'kind':'barcode','code':CODE},{'kind':'retailer','code':'00042'}],name='Другое молоко',shop_name='Соседи')
    assert second.status_code==201,second.text
    assert lookup(client,[{'kind':'retailer','code':'00042'}])['items'][0]['product_id']==first.json()['receipt_items'][0]['product_id']
    assert lookup(client,[{'kind':'retailer','code':'00042'}],'Соседи')['items'][0]['product_id']==second.json()['receipt_items'][0]['product_id']
    result=lookup(client,[{'kind':'barcode','code':CODE},{'kind':'retailer','code':'00042'}])
    assert len(result['items'])==2 and not result['auto_match']
    assert not lookup(client,[{'kind':'unknown','code':'000042'}])['items']


def test_invalid_archived_weight_and_foreign_variants(client):
    p=product(client);v=variant(client,p).json()['variants'][0]
    bad=lookup(client,[{'kind':'barcode','code':'4006381333932'}])
    assert bad['warnings'] and not bad['auto_match'] and not bad['items']
    assert receipt(client,[{'kind':'barcode','code':'4006381333932'}]).status_code==400
    client.put(f"/api/v1/operations/catalog-products/{p}/variants/{v['id']}",json={**v,'is_archived':True})
    assert not lookup(client,[{'kind':'barcode','code':CODE}])['items']
    prefix='223186022940'
    weight=prefix+str((10-sum(int(n)*(3 if i%2==0 else 1) for i,n in enumerate(reversed(prefix)))%10)%10)
    weighted=receipt(client,[{'kind':'barcode','code':weight}],name='Колбаса')
    assert weighted.status_code==201,weighted.text
    result=lookup(client,[{'kind':'barcode','code':weight}])
    assert not result['items'] and not result['auto_match'] and result['warnings']
    assert weighted.json()['receipt_items'][0]['receipt_codes']==[{'kind':'barcode','code':weight}]
    assert receipt(client,[{'kind':'barcode','code':weight}],name='Другой весовой товар',shop_name='Соседи').status_code==201


def test_plan_code_registration_and_confirmation_preserve_identity(client):
    result=client.post('/api/v1/plans',json={'kind':'expense','scheduled_date':'2026-10-20','receipt_items':[
        {'name':'Молоко','shop_name':'Green','quantity':'1','unit_price':'3.10','catalog_codes':[{'kind':'barcode','code':CODE}]}]})
    assert result.status_code==201,result.text
    row=result.json()['receipt_items'][0]
    assert row['variant_snapshot']['codes']==[CODE]
    assert lookup(client,[{'kind':'barcode','code':CODE}])['items'][0]['product_id']==row['product_id']
    confirmed=client.post(f"/api/v1/plans/{result.json()['id']}/confirm")
    assert confirmed.status_code==200,confirmed.text
    saved=confirmed.json()['operation']['receipt_items'][0]
    assert saved['product_id']==row['product_id']
    assert saved['variant_snapshot']==row['variant_snapshot']


def test_existing_sku_without_variant_corroborates_barcode_and_conflicts_do_not_reassign(client):
    p=product(client);s=_source(client,'Green')
    from tests.api.test_catalog_product_linkage_api import _operation
    op=_operation(client,product_id=p,source_id=s,name='Молоко',price='3',operation_date='2026-10-01')
    offer=op['receipt_items'][0]['template_id']
    assert variant(client,p).status_code==201
    endpoint=f'/api/v1/operations/catalog-products/{p}/offers/{offer}/identity'
    assert client.put(endpoint,json={'retailer_code':'sku-1'}).status_code==200
    result=lookup(client,[{'kind':'barcode','code':CODE},{'kind':'retailer','code':'sku-1'}])
    assert len(result['items'])==1 and result['auto_match']
    assert set(result['items'][0]['matched_by'])=={'barcode','retailer'}
    denied=receipt(client,[{'kind':'retailer','code':'sku-1'}],name='Другой товар')
    assert denied.status_code==400,denied.text
    assert get(client,p)['offers'][0]['retailer_code']=='sku-1'
    # A direct type choice is required to persist a damaged/uncertain OCR candidate.
    assert receipt(client,[{'kind':'unknown','code':'1234567'}]).status_code==422


def test_barcode_without_sku_links_existing_product_offer_and_survives_card_save(client):
    from tests.api.test_product_primary_codes_api import create
    p = create(client, sale_unit='piece', package_quantity='45', package_unit='g').json()['id']
    saved = receipt(client, [{'kind':'barcode','code':CODE}], product_id=p,
                    sale_unit=None, package_quantity=None, package_unit=None)
    assert saved.status_code == 201, saved.text
    row = saved.json()['receipt_items'][0]
    identity = get(client, p)
    v = identity['variants'][0]
    mapping = identity['offers'][0]
    assert mapping['template_id'] == row['template_id']
    assert mapping['variant_id'] == v['id'] == row['variant_snapshot']['variant_id']
    assert mapping['retailer_code'] is None
    assert v['codes'] == [CODE] and v['package_quantity'] is None
    found = lookup(client, [{'kind':'barcode','code':CODE}])
    assert found['items'][0]['template_id'] == row['template_id']
    edited = client.patch(f'/api/v1/operations/catalog-products/{p}', json={
        'codes': {'barcodes':[{'variant_id':v['id'], 'codes':[CODE]}]}})
    assert edited.status_code == 200, edited.text
    assert edited.json()['package_quantity'] == '45.000'
    assert get(client, p)['variants'][0]['codes'] == [CODE]
    old = client.get(f"/api/v1/operations/{saved.json()['id']}").json()
    assert old['receipt_items'][0]['variant_snapshot'] == row['variant_snapshot']
    assert old['receipt_total'] == saved.json()['receipt_total']


def test_barcode_only_fills_empty_mapping_without_overwriting_existing_metadata_or_package(client):
    from tests.api.test_product_primary_codes_api import create
    p = create(client, codes={'retailers':[{'shop_name':'Green','retailer_code':'sku-1'}]}).json()['id']
    mapping = get(client, p)['offers'][0]
    endpoint = f"/api/v1/operations/catalog-products/{p}/offers/{mapping['template_id']}/identity"
    assert client.put(endpoint, json={'retailer_code':'sku-1','external_name':'Milk','product_url':'https://example.com/milk'}).status_code == 200
    saved = receipt(client, [{'kind':'barcode','code':CODE}], product_id=p)
    assert saved.status_code == 201, saved.text
    first = get(client, p)['offers'][0]
    assert first['variant_id'] is not None
    assert first['retailer_code'] == 'sku-1' and first['external_name'] == 'Milk'
    assert first['product_url'] == 'https://example.com/milk'
    # A receipt for another package must not silently replace the shop's explicit mapping.
    other = receipt(client, [{'kind':'barcode','code':'5901234123457'}], product_id=p, package_quantity='1000')
    assert other.status_code == 201, other.text
    assert get(client, p)['offers'][0] == first
    assert other.json()['receipt_items'][0]['variant_snapshot']['variant_id'] != first['variant_id']


def test_internal_receipt_codes_preserve_stable_sku_and_money(client):
    # Actual 14-digit code printed by the till, plus a subsequent purchase code.
    original=receipt(client,[{'kind':'retailer','code':'1582951'}],name='Лук красный',
                     sale_unit='kg',package_quantity=None,package_unit=None)
    assert original.status_code==201,original.text
    owner=original.json()['receipt_items'][0]
    before=get(client,owner['product_id'])
    for code in ['22373102227750','2237310222750']:
        assert receipt(client,[{'kind':'barcode','code':code}]).status_code==400
        codes=[{'kind':'retailer','code':code}]
        response=receipt(client,codes,name='Лук красный',product_id=owner['product_id'],template_id=owner['template_id'],
                         quantity='0.370',unit_price='3.66',sale_unit='kg',package_quantity=None,package_unit=None)
        assert response.status_code==201,response.text
        operation=response.json();row=operation['receipt_items'][0]
        assert operation['receipt_total']=='1.35'
        assert float(row['quantity'])==.37 and row['unit_price']=='3.66'
        assert row['receipt_codes']==codes
        assert get(client,owner['product_id'])==before
        found=lookup(client,codes)
        assert not found['items'] and not found['auto_match'] and found['warnings']
        saved=client.get(f"/api/v1/operations/{operation['id']}").json()
        assert saved['receipt_items'][0]['receipt_codes']==codes
        stale={k:v for k,v in saved['receipt_items'][0].items() if k!='receipt_codes'}
        assert client.patch(f"/api/v1/operations/{operation['id']}",json={'receipt_items':[stale]}).status_code==400
        result=client.patch(f"/api/v1/operations/{operation['id']}",json={'receipt_items':saved['receipt_items']})
        assert result.status_code==200,result.text
        assert result.json()['receipt_total']=='1.35'
        assert result.json()['receipt_items'][0]['receipt_codes']==codes
        # The digits are not claimed as a globally or source-unique catalog identifier.
        other=receipt(client,codes,name='Другой весовой товар',shop_name='Green')
        assert other.status_code==201,other.text
        assert not any(v['codes'] for v in get(client,other.json()['receipt_items'][0]['product_id'])['variants'])
    # Genuine SKU conflicts remain actionable and atomic.
    denied=receipt(client,[{'kind':'retailer','code':'another-sku'}],name='Лук красный',
                   product_id=owner['product_id'],template_id=owner['template_id'])
    assert denied.status_code==400,denied.text
    assert '1582951' in denied.json()['detail']['message']
    assert get(client,owner['product_id'])==before


def test_internal_codes_survive_plan_confirmation_and_can_be_removed(client):
    codes=[{'kind':'retailer','code':'22373102227750'}]
    response=client.post('/api/v1/plans',json={'kind':'expense','scheduled_date':'2026-10-23','receipt_items':[
        {'name':'Лук','shop_name':'Green','quantity':'.37','unit_price':'3.66','sale_unit':'kg','catalog_codes':codes}]})
    assert response.status_code==201,response.text
    plan=response.json()
    assert plan['receipt_items'][0]['receipt_codes']==codes
    confirmed=client.post(f"/api/v1/plans/{plan['id']}/confirm")
    assert confirmed.status_code==200,confirmed.text
    operation=confirmed.json()['operation'];row=operation['receipt_items'][0]
    assert row['receipt_codes']==codes and operation['receipt_total']=='1.35'
    changed=client.patch(f"/api/v1/operations/{operation['id']}",json={'receipt_items':[{**row,'catalog_codes':[],'receipt_codes':[]}]})
    assert changed.status_code==200,changed.text
    assert changed.json()['receipt_items'][0]['receipt_codes']==[]


def test_internal_classifier_does_not_capture_valid_gtin14():
    from app.services.receipt_code_service import variable_code
    assert variable_code('22373102227750') and variable_code('02237310222750')
    assert not variable_code('24006381333935')  # Valid GTIN-14 with an indicator digit.
    assert not variable_code('1582951') and not variable_code('2not-a-code00')
