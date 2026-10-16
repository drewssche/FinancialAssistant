import json
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select
from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.main import app
from app.db.models.catalog_watch import CatalogOfferWatch, CatalogPriceEvent
from app.db.models.auth_identity import AuthIdentity
from app.services.catalog_watch_service import CatalogWatchService, now
from app.services import edostavka_provider as provider
from tests.api.test_catalog_product_linkage_api import client
from tests.api.test_product_primary_codes_api import create

URL='https://edostavka.by/product/870666'


def document(price='7.99', available=True, size='125'):
    p={'productId':870666,'productName':'Сыр 125 г','price':{'basePrice':10.99,'discountedPrice':price,'measurePrice':'63,92 BYN/кг'},'quantityInfo':{'measure':'шт'},'soldByWeight':False,'restInformation':{'isAvailable':available},'additionalProperties':[{'groupProperty':[{'propertyName':'Вес, гр','propertyValue':[size]}]}]}
    return '<script id="__NEXT_DATA__" type="application/json">'+json.dumps({'props':{'pageProps':{'productData':{'product':p}}}})+'</script>'


def snapshot(price='7.99', available=True, size='125'):
    return provider.parse_product(document(price,available,size),URL)


@pytest.fixture
def linked(client, monkeypatch):
    monkeypatch.setattr(provider,'fetch_product',lambda url:snapshot())
    # API module imports the provider function directly for preview.
    monkeypatch.setattr('app.api.v1.catalog_watch.fetch_product',lambda url:snapshot())
    p=create(client,codes={'retailers':[{'shop_name':'Е-доставка','retailer_code':'870666'}]}).json()
    pid=p['id'];tid=p['offers'][0]['id'];s=snapshot()
    r=client.put(f'/api/v1/catalog-watches/{pid}/offers/{tid}',json={'url':URL,'expected_key':s['comparison_key'],'expected_name':s['name']})
    assert r.status_code==200,r.text
    return pid,tid


def database():
    return next(app.dependency_overrides[get_db]())


def test_provider_price_not_discount_amount_and_no_arbitrary_urls():
    s=snapshot();assert s['price']=='7.99' and s['regular_price']=='10.99'
    assert s['available'] and s['size']==[['Вес, гр',['125']]]
    for url in ['http://edostavka.by/product/1','https://edostavka.by.evil.test/product/1','https://127.0.0.1/product/1','https://edostavka.by@127.0.0.1/product/1','https://edostavka.by/product/1/../../x']:
        with pytest.raises(ValueError):provider.canonical_url(url)
    assert provider.canonical_url(URL+'?utm_source=x')==URL
    for html in ['<h1>Unavailable</h1>',document('0'),document('NaN'),document('10000000')]:
        with pytest.raises(provider.RetailerUnavailable):provider.parse_product(html,URL)
    with pytest.raises(provider.RetailerUnavailable):provider.parse_product(document(),URL+'1')


def test_toggle_linking_ownership_and_baseline(client,linked):
    pid,tid=linked;base=f'/api/v1/catalog-watches/{pid}'
    d=client.get(base).json();assert not d['enabled'] and len(d['offers'])==1
    assert client.get('/api/v1/catalog-watches').json()['tracked_count']==0
    assert client.put(base,json={'enabled':True}).json()['enabled']
    dashboard=client.get('/api/v1/catalog-watches').json()
    assert dashboard['tracked_count']==1 and dashboard['events']==[] and len(dashboard['offers'])==1
    s=snapshot();r=client.put(base+f'/offers/{tid}',json={'url':URL,'expected_key':'changed','expected_name':s['name']});assert r.status_code==400
    app.dependency_overrides[get_current_user_id]=lambda:2
    for method,path,body in [('get',base,None),('put',base,{'enabled':True}),('post',base+'/preview',{'url':URL}),('delete',base+f'/offers/{tid}',None)]:
        r=getattr(client,method)(path,**({'json':body} if body else {}));assert r.status_code==404
    assert client.get('/api/v1/catalog-watches').json()['tracked_count']==0


def test_changes_errors_dedupe_and_unsubscribe(client,linked,monkeypatch):
    pid,tid=linked;base=f'/api/v1/catalog-watches/{pid}'
    client.put(base,json={'enabled':True})
    with database() as db:
        service=CatalogWatchService(db);w=db.get(CatalogOfferWatch,tid)
        db.add(AuthIdentity(user_id=1,provider='telegram',provider_user_id='12345'));db.commit()
        service.record(w,snapshot());assert list(service.deliveries())==[]
        service.record(w,snapshot('6.99'));service.record(w,snapshot('6.99'))
        events=list(db.scalars(select(CatalogPriceEvent)));assert len(events)==1
        monkeypatch.setattr('app.services.catalog_watch_service.now',lambda: now()+timedelta(minutes=16))
        deliveries=list(service.deliveries());assert len(deliveries)==1 and '7.99 → 6.99' in deliveries[0][2]
        events[0].telegram_sent_at=now();db.commit();assert list(service.deliveries())==[]
        # An unavailable/changed-size price is not a comparable price drop.
        service.record(w,snapshot('6.99',False));service.record(w,snapshot('5.99'))
        service.record(w,snapshot('4.99',size='100'));assert len(list(db.scalars(select(CatalogPriceEvent))))==1
        service.record(w,snapshot('5.99',size='100'))
        monkeypatch.setattr('app.services.catalog_watch_service.now',lambda: now()+timedelta(minutes=32))
        assert len(list(service.deliveries()))==1
        monkeypatch.setattr(provider,'fetch_product',lambda url:(_ for _ in ()).throw(provider.RetailerUnavailable('Недоступен')))
        old=deepcopy(w.snapshot);w.next_check_at=now()-timedelta(hours=1);db.commit();service.refresh_due()
        assert w.snapshot==old and w.error=='Недоступен'
    client.put(base,json={'enabled':False})
    with database() as db:assert list(CatalogWatchService(db).deliveries())==[]
    client.put(base,json={'enabled':True})
    with database() as db:assert list(CatalogWatchService(db).deliveries())==[]
    assert client.delete(base+f'/offers/{tid}').status_code==200
    d=client.get('/api/v1/catalog-watches').json();assert d['offers']==[] and len(d['unlinked'])==1


def test_detach_excludes_old_offer(client,linked):
    from app.db.models.operation_item_template import OperationItemTemplate
    pid,tid=linked
    client.put(f'/api/v1/catalog-watches/{pid}',json={'enabled':True})
    with database() as db:
        t=db.get(OperationItemTemplate,tid);t.product_id=None;db.commit()
    assert client.get('/api/v1/catalog-watches').json()['offers']==[]


def test_different_source_cannot_be_silently_labeled_edostavka(client,monkeypatch):
    p=create(client,codes={'retailers':[{'shop_name':'Green','retailer_code':'123'}]}).json()
    monkeypatch.setattr(provider,'fetch_product',lambda url:pytest.fail('Unsupported source must not fetch'))
    r=client.put(f"/api/v1/catalog-watches/{p['id']}/offers/{p['offers'][0]['id']}",json={'url':URL,'expected_key':'x','expected_name':'x'})
    assert r.status_code==400 and 'источник' in r.text


def test_telegram_failure_retains_pending_then_success_acknowledges(client,linked,monkeypatch):
    import asyncio
    import scripts.run_telegram_admin_bot as bot
    pid,tid=linked
    client.put(f'/api/v1/catalog-watches/{pid}',json={'enabled':True})
    with database() as db:
        service=CatalogWatchService(db);w=db.get(CatalogOfferWatch,tid)
        db.add(AuthIdentity(user_id=1,provider='telegram',provider_user_id='123'));db.commit()
        service.record(w,snapshot('6.99'))
    monkeypatch.setattr('app.services.catalog_watch_service.now',lambda: now()+timedelta(minutes=16))
    monkeypatch.setattr(bot,'SessionLocal',database)
    class Transport:
        fail=True
        calls=[]
        async def call(self,method,payload):
            self.calls.append(payload)
            if self.fail:raise RuntimeError('Network unavailable')
    transport=Transport()
    asyncio.run(bot.process_catalog_watches(transport))
    with database() as db:assert len(list(CatalogWatchService(db).deliveries()))==1
    transport.fail=False
    asyncio.run(bot.process_catalog_watches(transport))
    with database() as db:assert list(CatalogWatchService(db).deliveries())==[]
    asyncio.run(bot.process_catalog_watches(transport));assert len(transport.calls)==2
    assert transport.calls[1]['chat_id']=='123' and '6.99' in transport.calls[1]['text']


def test_background_refresh_without_notifications_and_permanent_history(client,linked,monkeypatch):
    pid,tid=linked
    clock=[now()]
    monkeypatch.setattr('app.services.catalog_watch_service.now',lambda:clock[0])
    with database() as db:
        service=CatalogWatchService(db);w=db.get(CatalogOfferWatch,tid)
        # No CatalogWatch row at all: linking alone is enough for background prices.
        monkeypatch.setattr(provider,'fetch_product',lambda url:snapshot('6.99'))
        w.next_check_at=clock[0]-timedelta(seconds=1);db.commit();service.refresh_due()
        assert w.snapshot['price']=='6.99' and not list(db.scalars(select(CatalogPriceEvent)))
        service.set_enabled(1,pid,True)
        db.add(AuthIdentity(user_id=1,provider='telegram',provider_user_id='123'));db.commit()
        service.record(w,snapshot('5.99'))
        assert list(service.deliveries())==[]
        clock[0]+=timedelta(minutes=10);service.record(w,snapshot('5.49'))
        clock[0]+=timedelta(minutes=10);assert list(service.deliveries())==[]
        clock[0]+=timedelta(minutes=6)
        batch=list(service.deliveries());assert len(batch)==1 and len(batch[0][1])==2
        for event in batch[0][1]:event.telegram_sent_at=clock[0]
        db.commit();assert list(service.deliveries())==[]
        service.set_enabled(1,pid,False)
        service.record(w,snapshot('4.99'))
        assert w.snapshot['price']=='4.99' and len(service.dashboard(1)['events'])==2
        service.set_enabled(1,pid,True)
        assert list(service.deliveries())==[] and len(service.dashboard(1)['events'])==2
        # Cursor history is permanent and isolated by owner.
        for i in range(23):service.record(w,snapshot(str(Decimal('4.98')-Decimal(i)/100)))
        first=service.dashboard(1);second=service.dashboard(1,first['next_cursor'])
        assert len(first['events'])==20 and len(second['events'])==5 and second['next_cursor'] is None
        assert not ({e['id'] for e in first['events']} & {e['id'] for e in second['events']})
        assert service.dashboard(2)['events']==[]
        # Even when changes keep coming, the oldest event is delivered within an hour.
        clock[0]+=timedelta(hours=1)
        service.record(w,snapshot('3.99'))
        assert list(service.deliveries())
