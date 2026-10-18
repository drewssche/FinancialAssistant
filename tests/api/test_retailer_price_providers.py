import json
from copy import deepcopy
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from app.services import retailer_price_provider as provider
from app.services.catalog_watch_service import CatalogWatchService, now
from app.db.models.catalog_watch import CatalogOfferWatch, CatalogPriceEvent
from app.db.models.catalog_identity import CatalogOfferIdentity
from app.db.models.auth_identity import AuthIdentity
from tests.api.test_catalog_watch_api import database
from tests.api.test_catalog_product_linkage_api import client
from tests.api.test_product_primary_codes_api import create

GREEN = 'https://green-dostavka.by/product/moloko-123/'
SOSEDI = 'https://sosedi-dostavka.by/products/moloko-456'


def mapping(d):
    return {'__iterable': 'Map', 'data': list(d.items())}


def green_data():
    return {'product': mapping({'item': {'id': 5, 'slug': 'moloko-123', 'vendorCode': '123', 'title': 'Молоко 900 мл', 'unit': 'piece', 'volume': '900мл', 'altUnit': 900, 'measur': 'л', 'gtin': '4810000000001'}, 'storeProduct': {'productId': 5, 'storeId': 2, 'price': 359, 'priceWithSale': 299, 'previousPrice': 199, 'isActive': True, 'balance': 4, 'bonusCardDiscountPrice': 249}}), 'store': mapping({'stores': mapping({'2': mapping({'name': 'Глебки, 5'})})})}


def green_html(d):
    return '<script id="__NEXT_DATA__">'+json.dumps({'props': {'initialState': json.dumps(d)}})+'</script>'


def sosedi_data():
    return {'product': {'id': 456, 'slug': 'moloko-456', 'name': 'Молоко 900 мл', 'price': 3.59, 'priceDiscount': 2.99, 'discount': 17, 'currencyISO': 'BYN', 'status': 1, 'isWait': 0, 'qty': 5, 'weight': '0.9', 'liter': 1, 'isWeightGoods': 0, 'cod': '4810000000001'}, 'darkstore': {'id': 1, 'name': 'Калиновского, 66А'}}


def sosedi_html(d):
    return '<script>window.SERVER_DATA='+json.dumps(d)+';</script>'


@pytest.mark.parametrize('key,url,build,html,parse', [
    ('green', GREEN, green_data, green_html, provider.parse_green),
    ('sosedi', SOSEDI, sosedi_data, sosedi_html, provider.parse_sosedi),
])
def test_public_price_identity_and_store_context(key,url,build,html,parse):
    d=build();s=parse(html(d),url)
    assert s['price']=='2.99' and s['regular_price']=='3.59' and s['available']
    assert s['provider']==key and s['unit']=='шт.' and 'Публичная' in s['conditions']
    with pytest.raises(ValueError):parse('<html>Unavailable</html>',url)
    with pytest.raises(ValueError):parse(html(d),url.replace('moloko','bread'))
    d=build()
    if key=='green':
        p=provider.unpack(d['product']);p['storeProduct']['priceWithSale']=0
    else:d['product']['price']='NaN'
    with pytest.raises(ValueError):parse(html(d),url)
    d=build()
    if key=='green':provider.unpack(d['product'])['storeProduct']['balance']=-71
    else:d['product']['qty']=0
    assert not parse(html(d),url)['available']
    d=build()
    if key=='green':provider.unpack(d['product'])['item']['volume']='800мл'
    else:d['product']['weight']='0.8'
    assert parse(html(d),url)['comparison_key']!=s['comparison_key']


def test_weight_price_basis_and_discount_conditions():
    d=green_data();p=provider.unpack(d['product']);p['item'].update(unit='weight',volume='0,3–0,6кг',altUnit=0)
    s=provider.parse_green(green_html(d),GREEN)
    assert s['unit']=='кг' and s['price']=='2.99'
    # Loyalty price, cashback, and previousPrice are not the public price.
    p['storeProduct']['bonusCardDiscountPrice']=100
    assert provider.parse_green(green_html(d),GREEN)['comparison_key']==s['comparison_key']
    d=sosedi_data();d['product'].update(isWeightGoods=1,liter=0,weight='0.6',price=2.99,priceDiscount=2.57,pricePerKg=4.99)
    s=provider.parse_sosedi(sosedi_html(d),SOSEDI)
    assert s['unit']=='0,6 кг' and s['price']=='2.57' and s['regular_price']=='2.99'
    d['darkstore']['id']=10
    changed=provider.parse_sosedi(sosedi_html(d),SOSEDI)
    assert changed['comparison_key']!=s['comparison_key'] and changed['conditions_key']!=s['conditions_key']
    d['product']['priceDiscount']=0
    assert provider.parse_sosedi(sosedi_html(d),SOSEDI)['price']=='2.99'


@pytest.mark.parametrize('url', [
    'http://green-dostavka.by/product/x-1/', 'https://green-dostavka.by.evil.com/product/x-1/',
    'https://green-dostavka.by@127.0.0.1/product/x-1/', 'https://sosedi-dostavka.by/products/../admin-1',
    'https://sosedi-dostavka.by/products/x%2f-1', 'https://127.0.0.1/products/x-1',
    'https://sosedi-dostavka.by:443/products/x-1',
])
def test_untrusted_urls_never_fetch(url,monkeypatch):
    monkeypatch.setattr(httpx,'Client',lambda **kw:pytest.fail('Must validate before networking'))
    with pytest.raises(ValueError):provider.fetch_product(url)


@pytest.mark.parametrize('response', ['redirect', 'large', 'bad', 'timeout'])
def test_bounded_fetch_failures(response,monkeypatch):
    calls=[];real=httpx.Client
    def handle(request):
        calls.append(str(request.url))
        if response=='timeout':raise httpx.ReadTimeout('timeout')
        if response=='redirect':return httpx.Response(302,headers={'location':'http://127.0.0.1/private'})
        return httpx.Response(200,content=b'x'*3_000_001 if response=='large' else b'Unavailable')
    monkeypatch.setattr(httpx,'Client',lambda **kw:real(**kw,transport=httpx.MockTransport(handle)))
    with pytest.raises(provider.RetailerUnavailable):provider.fetch_product(GREEN+'?utm_source=x')
    assert calls==[GREEN]


def test_multi_source_refresh_dashboard_delivery_and_failure(client,monkeypatch):
    p=create(client,codes={'retailers':[{'shop_name':'Green','retailer_code':'123'},{'shop_name':'Соседи','retailer_code':'456'}]}).json()
    pid=p['id'];tids=[o['id'] for o in p['offers']];base=f'/api/v1/catalog-watches/{pid}'
    snapshots={GREEN:provider.parse_green(green_html(green_data()),GREEN),SOSEDI:provider.parse_sosedi(sosedi_html(sosedi_data()),SOSEDI)}
    monkeypatch.setattr(provider,'fetch_product',lambda url:deepcopy(snapshots[url]))
    with database() as db:
        db.get(CatalogOfferIdentity,tids[0]).product_url=GREEN;db.commit()
    detail=client.get(base).json()
    assert detail['supported_offers'][str(tids[0])]['saved_url']==GREEN
    assert detail['supported_offers'][str(tids[1])]['source']=='Соседи'
    for tid,url in zip(tids,[GREEN,SOSEDI]):
        s=snapshots[url]
        assert client.put(base+f'/offers/{tid}',json={'url':url,'expected_key':s['comparison_key'],'expected_name':s['name']}).status_code==200
    assert client.get('/api/v1/catalog-watches').json()['events']==[]
    client.put(base,json={'enabled':True})
    with database() as db:
        db.add(AuthIdentity(user_id=1,provider='telegram',provider_user_id='123'));db.commit()
        service=CatalogWatchService(db)
        for url,price in [(GREEN,'2.79'),(SOSEDI,'3.19')]:snapshots[url]['price']=price
        for tid in tids:db.get(CatalogOfferWatch,tid).next_check_at=now()-timedelta(minutes=1)
        db.commit();service.refresh_due()
        events=list(db.scalars(select(CatalogPriceEvent).where(CatalogWatchService.notification_events())));assert len(events)==2
        monkeypatch.setattr('app.services.catalog_watch_service.now',lambda: now()+timedelta(minutes=16))
        message=list(service.deliveries())[0][2]
        assert 'Green' in message and 'Соседи' in message and '2.99 → 2.79' in message and '2.99 → 3.19' in message
        assert len(message)<4096
        # No duplicate or synthetic decrease on failures, changed size/store or unavailability.
        for tid in tids:service.record(db.get(CatalogOfferWatch,tid),snapshots[db.get(CatalogOfferWatch,tid).url])
        assert len(list(db.scalars(select(CatalogPriceEvent).where(CatalogWatchService.notification_events()))))==2
        w=db.get(CatalogOfferWatch,tids[0]);old=deepcopy(w.snapshot)
        monkeypatch.setattr(provider,'fetch_product',lambda url:(_ for _ in ()).throw(ValueError('Недоступен')))
        w.next_check_at=now()-timedelta(minutes=1);db.commit();service.refresh_due()
        assert w.snapshot==old and w.error=='Недоступен'
        changed={**old,'price':'1.00','comparison_key':'different store'};service.record(w,changed)
        assert len(list(db.scalars(select(CatalogPriceEvent).where(CatalogWatchService.notification_events()))))==2
    dashboard=client.get('/api/v1/catalog-watches').json()
    assert {e['source'] for e in dashboard['events']}=={'Green','Соседи'}
    client.put(base,json={'enabled':False})
    with database() as db:assert list(CatalogWatchService(db).deliveries())==[]


def test_telegram_batches_long_store_urls(client,monkeypatch):
    p=create(client,codes={'retailers':[{'shop_name':'Green','retailer_code':'123'}]}).json()
    pid=p['id'];tid=p['offers'][0]['id'];s=provider.parse_green(green_html(green_data()),GREEN)
    monkeypatch.setattr(provider,'fetch_product',lambda url:deepcopy(s))
    base=f'/api/v1/catalog-watches/{pid}'
    assert client.put(base+f'/offers/{tid}',json={'url':GREEN,'expected_key':s['comparison_key'],'expected_name':s['name']}).status_code==200
    client.put(base,json={'enabled':True})
    with database() as db:
        db.add(AuthIdentity(user_id=1,provider='telegram',provider_user_id='123'));db.commit()
        service=CatalogWatchService(db);w=db.get(CatalogOfferWatch,tid)
        for price in ['2.79','2.59','2.39','2.19']:
            service.record(w,{**s,'price':price,'url':'https://green-dostavka.by/product/'+'a'*1700+'-123/'})
        monkeypatch.setattr('app.services.catalog_watch_service.now',lambda: now()+timedelta(minutes=16))
        deliveries=list(service.deliveries())
        assert len(deliveries)==4
        assert sum(len(batch) for _,batch,_ in deliveries)==4
        assert all(len(message.encode('utf-16-le'))//2<=3800 for _,_,message in deliveries)


def test_decimal_size_in_url_is_valid_but_path_traversal_is_not():
    url='https://sosedi-dostavka.by/products/orbit-13.6g-300368343'
    assert provider.identify_url(url)==('sosedi',url)
    for path in ['../orbit-123','x/../orbit-123','orbit%2f-123']:
        with pytest.raises(ValueError):provider.identify_url('https://sosedi-dostavka.by/products/'+path)


def test_green_unicode_slug_roundtrips_encoded_browser_url():
    from urllib.parse import quote
    url='https://green-dostavka.by/product/moloko-№1-123/'
    assert provider.identify_url(quote(url,safe=':/'))==('green',url)
    with pytest.raises(ValueError):provider.identify_url('https://green-dostavka.by/product/x%2f..%2fy-123/')
