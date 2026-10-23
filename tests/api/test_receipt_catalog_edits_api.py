from decimal import Decimal
from app.api.deps import get_current_user_id
from app.main import app
from tests.api.test_catalog_product_linkage_api import client, _source, _brand, _category
from tests.api.test_catalog_identity_api import CODE, get


def setup(client):
    p=client.post('/api/v1/operations/catalog-products',json={'name':'Молоко 900мл','sale_unit':'piece','package_quantity':'900','package_unit':'ml'}).json()['id']
    source=_source(client,'Green')
    row={'product_id':p,'source_id':source,'shop_name':'Green','name':'Молоко 900мл','sale_unit':'piece','package_quantity':'900','package_unit':'ml','quantity':'2','unit_price':'3','catalog_codes':[{'kind':'barcode','code':CODE}]}
    old=save(client,row).json();v=old['receipt_items'][0]['variant_snapshot']['variant_id']
    row.update(template_id=old['receipt_items'][0]['template_id'])
    return p,row,old,v


def save(client,row):
    return client.post('/api/v1/operations',json={'kind':'expense','operation_date':'2026-10-23','receipt_items':[row]})


def test_inline_edits_update_card_atomically_and_keep_old_purchase(client):
    p,row,old,v=setup(client)
    brand=_brand(client,'Новый бренд');cat=_category(client,'Молочные продукты')
    changed={**row,'name':'Молоко новое 800мл','sale_unit':'pack','package_quantity':'800','brand_id':brand,'category_id':cat,'category_touched':True,
             'catalog_name_touched':True,'catalog_measurement_touched':True,'catalog_edit_variant_id':v}
    result=save(client,changed);assert result.status_code==201,result.text
    current=result.json()['receipt_items'][0]
    assert current['product_id']==p and current['template_id']==row['template_id']
    assert Decimal(current['unit_price'])==3 and Decimal(current['quantity'])==2
    assert Decimal(result.json()['amount'])==6
    card=client.get(f'/api/v1/operations/catalog-products/{p}').json()
    assert card['name']=='Молоко новое 800мл' and card['sale_unit']=='pack'
    assert Decimal(card['package_quantity'])==800 and card['category_id']==cat and card['brand_id']==brand
    history=get(client,p)['variants'];assert len(history)==2
    previous=next(x for x in history if x['id']==v)
    assert Decimal(previous['package_quantity'])==900 and previous['sale_unit']=='piece'
    assert current['variant_snapshot']['variant_id']!=v and current['variant_snapshot']['codes']==[CODE]
    past=client.get(f"/api/v1/operations/{old['id']}").json()['receipt_items'][0]
    original=old['receipt_items'][0]
    for field in ['name','sale_unit','package_quantity','package_unit','unit_price','quantity','line_total','variant_snapshot']:
        assert past[field]==original[field],field
    # Repeating an explicit edit is idempotent, including the original variant ID.
    assert save(client,changed).status_code==201
    assert len(get(client,p)['variants'])==2
    edited=client.patch(f"/api/v1/operations/{old['id']}",json={'receipt_items':[{**past,'quantity':'3'}]})
    assert edited.status_code==200,edited.text
    assert edited.json()['receipt_items'][0]['variant_snapshot']==original['variant_snapshot']
    card=client.get(f'/api/v1/operations/catalog-products/{p}').json()
    assert card['name']=='Молоко новое 800мл' and card['offers'][0]['name']=='Молоко новое 800мл'


def test_no_implicit_card_resize_and_failed_save_rolls_back_edits(client):
    p,row,old,v=setup(client)
    ordinary={**row,'catalog_codes':[],'package_quantity':'750'}
    assert save(client,ordinary).status_code==201
    assert Decimal(client.get(f'/api/v1/operations/catalog-products/{p}').json()['package_quantity'])==900
    result=save(client,{**row,'catalog_name_touched':True,'catalog_measurement_touched':True,'catalog_edit_variant_id':v,'name':'Не сохранять','package_quantity':'800','catalog_codes':[{'kind':'barcode','code':'1234'}]})
    assert result.status_code==400,result.text
    card=client.get(f'/api/v1/operations/catalog-products/{p}').json()
    assert card['name']=='Молоко 900мл' and Decimal(card['package_quantity'])==900
    assert len(get(client,p)['variants'])==1
    assert get(client,p)['variants'][0]['codes']==[CODE]
    assert client.get(f"/api/v1/operations/{old['id']}").json()==old


def test_foreign_variant_and_mismatched_template_cannot_be_edited(client):
    p,row,old,v=setup(client)
    other=client.post('/api/v1/operations/catalog-products',json={'name':'Другой товар'}).json()['id']
    foreign=client.post(f'/api/v1/operations/catalog-products/{other}/variants',json={'name':'1 шт','sale_unit':'piece','codes':[]}).json()['variants'][0]['id']
    result=save(client,{**row,'catalog_measurement_touched':True,'catalog_edit_variant_id':foreign,'package_quantity':'800'})
    assert result.status_code==400,result.text
    result=save(client,{**row,'product_id':other,'catalog_name_touched':True,'name':'Подмена'})
    assert result.status_code==400,result.text
    app.dependency_overrides[get_current_user_id]=lambda:2
    try: assert save(client,{**row,'catalog_name_touched':True,'name':'Чужой'}).status_code==400
    finally: app.dependency_overrides[get_current_user_id]=lambda:1
    assert client.get(f'/api/v1/operations/catalog-products/{p}').json()['name']=='Молоко 900мл'


def test_new_barcode_preserves_old_code_and_other_store_package(client):
    p,row,old,v=setup(client)
    other={**row,'source_id':_source(client,'Другой магазин'),'shop_name':'Другой магазин','catalog_codes':[]}
    other.pop('template_id')
    second=save(client,other);assert second.status_code==201,second.text
    result=save(client,{**row,'catalog_measurement_touched':True,'catalog_edit_variant_id':v,'package_quantity':'800',
        'catalog_codes':[{'kind':'barcode','code':'4811040140757'}]})
    assert result.status_code==201,result.text
    identities=get(client,p);previous=next(x for x in identities['variants'] if x['id']==v)
    assert previous['codes']==[CODE]
    target=result.json()['receipt_items'][0]['variant_snapshot']['variant_id']
    assert next(x for x in identities['variants'] if x['id']==target)['codes']==['4811040140757']
    other_mapping=next(x for x in identities['offers'] if x['template_id']==second.json()['receipt_items'][0]['template_id'])
    assert other_mapping['variant_id']==v
