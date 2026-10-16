from tests.api.test_catalog_product_linkage_api import client
from tests.api.test_catalog_identity_api import get, CODE


def create(client, **fields):
    return client.post('/api/v1/operations/catalog-products', json={'name':'Молоко','sale_unit':'pack','package_quantity':'900','package_unit':'ml',**fields})


def test_create_product_and_codes_together_then_edit_and_clear(client):
    response=create(client,codes={'barcodes':[{'codes':[CODE]}],'retailers':[{'shop_name':'Green','retailer_code':'000-42'}]})
    assert response.status_code==201,response.text
    p=response.json();identity=get(client,p['id']);v=identity['variants'][0];offer=identity['offers'][0]
    assert v['codes']==[CODE] and offer['retailer_code']=='000-42'
    assert p['offers'][0]['source_name']=='Green'
    # Editing the main product does not rewrite the selected package's measurements.
    changed=client.patch(f"/api/v1/operations/catalog-products/{p['id']}",json={'name':'Новое название','package_quantity':'1000','codes':{'barcodes':[{'variant_id':v['id'],'codes':['0'+CODE]}],'retailers':[{'template_id':offer['template_id'],'retailer_code':'00123'}]}})
    assert changed.status_code==200,changed.text
    identity=get(client,p['id']);assert identity['variants'][0]['package_quantity']=='900.000'
    assert identity['variants'][0]['codes']==['0'+CODE]
    assert identity['offers'][0]['retailer_code']=='00123'
    cleared=client.patch(f"/api/v1/operations/catalog-products/{p['id']}",json={'codes':{'barcodes':[{'variant_id':v['id'],'codes':[]}],'retailers':[{'template_id':offer['template_id'],'retailer_code':''}]}})
    assert cleared.status_code==200,cleared.text
    assert get(client,p['id'])['variants'][0]['codes']==[]
    assert get(client,p['id'])['offers'][0]['retailer_code'] is None


def test_identifier_conflict_rolls_back_name_and_new_product(client):
    first=create(client,codes={'barcodes':[{'codes':[CODE]}],'retailers':[{'shop_name':'Green','retailer_code':'000-42'}]}).json()
    second=create(client,name='Хлеб').json()
    bad=client.patch(f"/api/v1/operations/catalog-products/{second['id']}",json={'name':'Не должно сохраниться','codes':{'barcodes':[{'codes':[CODE]}]}})
    assert bad.status_code==400,bad.text
    assert client.get(f"/api/v1/operations/catalog-products/{second['id']}").json()['name']=='Хлеб'
    before=client.get('/api/v1/operations/catalog-products').json()['total']
    rejected=create(client,name='Другой товар',codes={'barcodes':[{'codes':['5901234123457']}],'retailers':[{'shop_name':'Green','retailer_code':'000-42'}]})
    assert rejected.status_code==400,rejected.text
    assert client.get('/api/v1/operations/catalog-products').json()['total']==before
    assert get(client,second['id'])=={'variants':[],'offers':[]}


def test_codes_cannot_edit_other_product_and_preserve_offer_extra_fields(client):
    first=create(client,codes={'barcodes':[{'codes':[CODE]}],'retailers':[{'shop_name':'Green','retailer_code':'001'}]}).json()
    identity=get(client,first['id']);v=identity['variants'][0];offer=identity['offers'][0]
    second=create(client,name='Хлеб').json()
    for edit in [{'barcodes':[{'variant_id':v['id'],'codes':[]}]},{'retailers':[{'template_id':offer['template_id'],'retailer_code':'bad'}]}]:
        result=client.patch(f"/api/v1/operations/catalog-products/{second['id']}",json={'codes':edit})
        assert result.status_code==400,result.text
    endpoint=f"/api/v1/operations/catalog-products/{first['id']}/offers/{offer['template_id']}/identity"
    assert client.put(endpoint,json={'retailer_code':'001','variant_id':v['id'],'external_name':'МОЛОКО','product_url':'https://example.com/milk'}).status_code==200
    changed=client.patch(f"/api/v1/operations/catalog-products/{first['id']}",json={'codes':{'retailers':[{'template_id':offer['template_id'],'retailer_code':'002'}]}})
    assert changed.status_code==200,changed.text
    saved=get(client,first['id'])['offers'][0]
    assert saved['variant_id']==v['id'] and saved['external_name']=='МОЛОКО' and saved['product_url']=='https://example.com/milk'


def test_size_change_records_history_and_keeps_receipt_snapshot(client):
    from tests.api.test_receipt_codes_api import receipt
    saved=receipt(client,[{'kind':'barcode','code':CODE}]).json()
    row=saved['receipt_items'][0];p=row['product_id']
    endpoint=f'/api/v1/operations/catalog-products/{p}'
    changed=client.patch(endpoint,json={'package_quantity':'800'})
    assert changed.status_code==200,changed.text
    assert changed.json()['package_quantity']=='800.000'
    history=client.get(f'/api/v1/activity?entity_type=catalog_product&entity_id={p}').json()['items']
    changes=[e for e in history if e['title']=='Размер товара изменён']
    assert len(changes)==1
    quantity=next(c for c in changes[0]['changes'] if c['field']=='package_quantity')
    assert float(quantity['old'])==900 and float(quantity['new'])==800
    old=client.get(f"/api/v1/operations/{saved['id']}").json()
    assert old['receipt_items'][0]['package_quantity']==row['package_quantity']
    assert old['receipt_items'][0]['variant_snapshot']==row['variant_snapshot']
    assert old['receipt_total']==saved['receipt_total']
    assert get(client,p)['variants'][0]['package_quantity']=='900.000'
    assert client.patch(endpoint,json={'package_quantity':'800'}).status_code==200
    history=client.get(f'/api/v1/activity?entity_type=catalog_product&entity_id={p}').json()['items']
    assert len([e for e in history if e['title']=='Размер товара изменён'])==1
    # A failed code registration also rolls back the size and its history event.
    failed=client.patch(endpoint,json={'package_quantity':'700','codes':{'barcodes':[{'codes':[CODE]}]}})
    assert failed.status_code==400,failed.text
    assert client.get(endpoint).json()['package_quantity']=='800.000'
    history=client.get(f'/api/v1/activity?entity_type=catalog_product&entity_id={p}').json()['items']
    assert len([e for e in history if e['title']=='Размер товара изменён'])==1
