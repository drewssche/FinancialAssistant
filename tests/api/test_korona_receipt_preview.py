from decimal import Decimal
import pytest
from app.services import korona_product_provider as korona
from app.services import receipt_site_service as site
from app.main import app
from app.api.deps import get_current_user_id
from tests.api.test_catalog_product_linkage_api import client
from tests.api.test_receipt_codes_api import receipt, lookup

CODES=[{'kind':'retailer','code':'2276384'}]
URL='https://korona.by/our-production/syrniki-blinciki/blinciki-s-tvorogom'
PRODUCT={'name':'Блинчики с творогом 500 г','category_url_alias':'syrniki-blinciki',
         'product_url_alias':'blinciki-s-tvorogom','image':{'url':'https://korona.by/uploads/product-image/test.png'},
         'composition':'<p>Блинчики с творогом</p>','caption':'Замороженный полуфабрикат'}


@pytest.fixture(autouse=True)
def public_catalogue(monkeypatch):
    import json
    korona.catalogue.cache_clear()
    monkeypatch.setattr(korona.retailer,'read_public',lambda url:json.dumps({'data':[PRODUCT]} if url.endswith('/products') else {'data':PRODUCT}))
    yield
    korona.catalogue.cache_clear()


def search(client,**extra):
    return client.post('/api/v1/operations/catalog-products/lookup-site-codes',json={
        'shop_name':'Корона','name':'Блинчики с творогом','codes':CODES,**extra})


def test_confirmation_saves_link_and_codes_atomically_without_price_watch(client):
    result=search(client);assert result.status_code==200,result.text
    candidate=result.json()['items'][0]
    assert candidate['matched_by']=='name' and candidate['requires_confirmation'] and candidate['price_unpublished']
    assert candidate['site_price'] is None and candidate['measurement']=={'package_quantity':'500','package_unit':'g'}
    assert client.get('/api/v1/operations/catalog-products').json()['total']==0
    operation=receipt(client,CODES,name='Блинчики с творогом',shop_name='Корона',sale_unit='piece',package_quantity=None,package_unit=None,
        unit_price='2.75',regular_unit_price='3.00',is_discounted=True,discount_mode='amount',discount_value='0.50',discount_type='promo',
        site_selection=candidate['site_selection'])
    assert operation.status_code==201,operation.text
    data=operation.json();row=data['receipt_items'][0]
    assert data['receipt_total']=='5.50' and row['quantity']=='2.000'
    assert Decimal(row['discount_value'])==Decimal('0.50') and Decimal(row['regular_unit_price'])==Decimal('3.00')
    identity=client.get(f"/api/v1/operations/catalog-products/{row['product_id']}/identity").json()['offers'][0]
    assert identity['product_url']==URL and identity['retailer_code']=='2276384'
    watch=client.get(f"/api/v1/catalog-watches/{row['product_id']}").json()
    assert watch['offers']==[] and watch['supported_offer_ids']==[]
    found=lookup(client,CODES,'Корона');assert found['auto_match'] and found['items'][0]['product_id']==row['product_id']
    assert lookup(client,CODES,'Соседи')['items']==[]
    repeat=search(client,name='Другое сокращение в чеке',template_id=row['template_id']).json()['items'][0]
    assert repeat['url']==URL and repeat['matched_by']=='saved_link' and not repeat['requires_confirmation']


@pytest.mark.parametrize('change',['code','store','owner','tamper'])
def test_changed_context_rejected_without_partial_operation(client,change):
    token=search(client).json()['items'][0]['site_selection'];codes=CODES;shop='Корона'
    if change=='code':codes=[{'kind':'retailer','code':'42'}]
    if change=='store':shop='Green'
    if change=='owner':app.dependency_overrides[get_current_user_id]=lambda:2
    if change=='tamper':token=token[:-10]+'xxxxxxxxxx'
    result=receipt(client,codes,shop_name=shop,site_selection=token)
    assert result.status_code==400,result.text
    assert client.get('/api/v1/operations').json()['total']==0


def test_without_confirmation_does_not_link_and_internal_codes_stay_store_scoped(client):
    codes=[{'kind':'internal','code':'2237310227750'}]
    item=search(client,codes=codes).json()['items'][0]
    first=receipt(client,codes,shop_name='Корона',name='Блинчики').json()['receipt_items'][0]
    identity=client.get(f"/api/v1/operations/catalog-products/{first['product_id']}/identity").json()['offers'][0]
    assert identity['product_url'] is None
    result=receipt(client,codes,shop_name='Корона',name='Блинчики',template_id=first['template_id'],product_id=first['product_id'],site_selection=item['site_selection'])
    assert result.status_code==201,result.text
    assert lookup(client,codes,'Корона')['auto_match']
    assert lookup(client,codes,'Green')['items']==[]


def test_no_codes_and_unavailable_site_are_supported(client,monkeypatch):
    assert search(client,codes=[]).json()['items']
    assert search(client,codes=[],name='').json()['state']=='missing_name'
    assert search(client,name='Ролл Калифорния').json()['state']=='not_found'
    monkeypatch.setattr(korona,'search',lambda *args,**kwargs:(_ for _ in ()).throw(ValueError('unavailable')))
    assert search(client).json()['state']=='unavailable'
    assert receipt(client,CODES,shop_name='Корона').status_code==201


def test_template_from_other_user_or_source_rejected(client):
    row=receipt(client,CODES,shop_name='Green').json()['receipt_items'][0]
    assert search(client,template_id=row['template_id']).status_code==400
    app.dependency_overrides[get_current_user_id]=lambda:2
    assert search(client,template_id=row['template_id']).status_code==404


def test_public_snapshot_url_validation_and_size_not_from_nutrition():
    assert korona.snapshot(PRODUCT)['url']==URL
    for url in ['https://koronaXby/our-production/a/b','https://korona.by.evil/our-production/a/b','https://korona.by/our-production/a/../b','http://korona.by/our-production/a/b','https://korona.by@evil/our-production/a/b','https://korona.by/our-production/a/b?url=http://localhost']:
        with pytest.raises(ValueError):korona.canonical_url(url)
    assert korona.snapshot(PRODUCT|{'name':'Блинчики','caption':'Замороженный полуфабрикат','composition':'Пищевая ценность на 100 г','jbu_title':'100 г'})['measurement'] is None


def test_name_search_requires_relevant_words_and_preserves_cache(monkeypatch):
    import json
    variants = [PRODUCT, PRODUCT | {'name': 'Блинчики с мясом'}, PRODUCT | {'name': 'Вареники с творогом'}]
    monkeypatch.setattr(korona.retailer, 'read_public', lambda url: json.dumps({'data': variants}))
    assert [item['name'] for item in korona.search('Блинчики с творогом')] == [PRODUCT['name']]
    assert len(korona.search('блинчики')) == 2
