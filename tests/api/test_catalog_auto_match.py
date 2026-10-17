from copy import deepcopy
import json
from datetime import timedelta
from sqlalchemy import select
import pytest
from app.api.deps import get_current_user_id
from app.main import app
from app.db.models.catalog_watch import CatalogOfferMatch, CatalogOfferWatch, CatalogPriceEvent
from app.db.models.operation_item_template import OperationItemTemplate
from app.db.models.catalog_identity import CatalogOfferIdentity, CatalogVariantCode
from app.services.catalog_match_service import CatalogMatchService
from app.services.catalog_watch_service import now
from app.services import retailer_price_provider as provider
from tests.api.test_catalog_product_linkage_api import client
from tests.api.test_product_primary_codes_api import create
from tests.api.test_catalog_watch_api import database
from tests.api.test_catalog_identity_api import CODE

URL = 'https://green-dostavka.by/product/milk-123/'


def card(url=URL, code=CODE, article='123'):
    return dict(url=url, name='Молоко 900 мл', price='2.99', regular_price='3.49', available=True,
                unit='шт.', currency='BYN', comparison_key=url, conditions_key='public',
                identifiers={'barcodes':[code], 'article':article})


def setup(client, monkeypatch, cards=None, article='123'):
    product=create(client,codes={'barcodes':[{'codes':[CODE]}], 'retailers':[{'shop_name':'Green','retailer_code':article}]}).json()
    cards=cards or [card()]
    monkeypatch.setattr(provider, 'search_products', lambda *args:[{'url':s['url']} for s in cards])
    monkeypatch.setattr(provider, 'fetch_product', lambda url:deepcopy(next(s for s in cards if s['url']==url)))
    return product['id'],product['offers'][0]['id']


def run(tid):
    with database() as db:
        return CatalogMatchService(db).discover(db.get(OperationItemTemplate,tid))


def test_exact_automatic_baseline_no_notification_and_no_overwrite(client,monkeypatch):
    pid,tid=setup(client,monkeypatch)
    client.put(f'/api/v1/catalog-watches/{pid}',json={'enabled':True})
    assert run(tid)
    data=client.get(f'/api/v1/catalog-watches/{pid}').json()
    assert data['offers'][0]['snapshot']['price']=='2.99'
    with database() as db:
        assert db.get(CatalogOfferMatch,tid).state=='linked'
        assert not list(db.scalars(select(CatalogPriceEvent)))
    monkeypatch.setattr(provider,'fetch_product',lambda url:pytest.fail('Existing connection is preserved'))
    assert not run(tid)


@pytest.mark.parametrize('cards,expected',[
    ([card(),card('https://green-dostavka.by/product/milk-456/',article='456')],'choice'),
    ([card(code='5901234123457')],'choice'),
    ([card(code='',article='999')],'choice'),
])
def test_ambiguity_conflicts_and_fuzzy_hits_never_auto_connect(client,monkeypatch,cards,expected):
    pid,tid=setup(client,monkeypatch,cards)
    assert run(tid)
    data=client.get(f'/api/v1/catalog-watches/{pid}').json()
    assert data['offers']==[]
    match=data['supported_offers'][str(tid)]['matching']
    assert match['state']==expected and len(match['candidates'])==len(cards)
    # Candidates survive another session / page reload.
    assert client.get(f'/api/v1/catalog-watches/{pid}').json()['supported_offers'][str(tid)]['matching']==match


def test_source_scope_and_current_package_only(client,monkeypatch):
    pid,tid=setup(client,monkeypatch)
    client.patch(f'/api/v1/operations/catalog-products/{pid}',json={'package_quantity':'800'})
    seen=[]
    monkeypatch.setattr(provider,'search_products',lambda key,q,kind:seen.append((key,q,kind)) or [])
    assert run(tid)
    assert seen==[('green','123','retailer')]


def test_errors_retry_and_code_changes_invalidate_results(client,monkeypatch):
    pid,tid=setup(client,monkeypatch)
    monkeypatch.setattr(provider,'fetch_product',lambda url:(_ for _ in ()).throw(ValueError('Недоступен')))
    assert run(tid)
    with database() as db:
        r=db.get(CatalogOfferMatch,tid);assert r.state=='error' and r.next_check_at>now().replace(tzinfo=None)
        assert not db.get(CatalogOfferWatch,tid)
    assert not run(tid)
    client.patch(f'/api/v1/operations/catalog-products/{pid}',json={'codes':{'retailers':[{'template_id':tid,'retailer_code':'456'}]}})
    assert client.get(f'/api/v1/catalog-watches/{pid}').json()['supported_offers'][str(tid)]['matching']['state']=='pending'


def test_disconnect_pauses_autolink_and_retry_requires_owner(client,monkeypatch):
    pid,tid=setup(client,monkeypatch);assert run(tid)
    assert client.delete(f'/api/v1/catalog-watches/{pid}/offers/{tid}').status_code==200
    assert not run(tid)
    app.dependency_overrides[get_current_user_id]=lambda:2
    assert client.post(f'/api/v1/catalog-watches/{pid}/offers/{tid}/autolink').status_code==404
    app.dependency_overrides[get_current_user_id]=lambda:1
    assert client.post(f'/api/v1/catalog-watches/{pid}/offers/{tid}/autolink').status_code==200
    assert run(tid)


def test_codes_changed_during_fetch_do_not_connect_stale_card(client,monkeypatch):
    pid,tid=setup(client,monkeypatch)
    def fetch(url):
        with database() as db:
            identity=db.get(CatalogOfferIdentity,tid);identity.retailer_code='789';db.commit()
        return card()
    monkeypatch.setattr(provider,'fetch_product',fetch)
    assert not run(tid)
    with database() as db:assert not db.get(CatalogOfferWatch,tid)


def test_truncated_search_never_auto_links_even_one_confirmed_hit(client,monkeypatch):
    cards=[card()]+[card(f'https://green-dostavka.by/product/milk-{i}/',code='',article=str(i)) for i in range(1000,1007)]
    _,tid=setup(client,monkeypatch,cards);assert run(tid)
    with database() as db:
        assert not db.get(CatalogOfferWatch,tid)
        assert db.get(CatalogOfferMatch,tid).state=='choice'


def test_provider_identity_evidence_is_from_product_card():
    import json
    from app.services import edostavka_provider
    from tests.api.test_catalog_watch_api import document, URL as EURL
    from tests.api.test_retailer_price_providers import green_data, green_html, sosedi_data, sosedi_html, GREEN, SOSEDI
    green=green_data()
    provider.unpack(green['product'])['item']['gtin']=CODE
    assert provider.parse_green(green_html(green),GREEN)['identifiers']=={'article':'123','barcodes':[CODE]}
    sosedi=sosedi_data();sosedi['product']['cod']=CODE
    assert provider.parse_sosedi(sosedi_html(sosedi),SOSEDI)['identifiers']=={'article':'456','barcodes':[CODE]}
    html=document().replace(json.dumps('Вес, гр'),json.dumps('Штрихкод')).replace('["125"]',json.dumps([CODE]))
    assert edostavka_provider.parse_product(html,EURL)['identifiers']=={'article':'870666','barcodes':[CODE]}


def test_exact_article_without_barcode_and_cross_source_rejection(client,monkeypatch):
    _,tid=setup(client,monkeypatch,[card(code='')])
    assert run(tid)
    with database() as db:assert db.get(CatalogOfferWatch,tid)
    # A separate Green offer cannot attach an E-delivery search result.
    p=create(client,name='Хлеб',codes={'retailers':[{'shop_name':'Green','retailer_code':'456'}]}).json()
    tid=p['offers'][0]['id']
    monkeypatch.setattr(provider,'search_products',lambda *args:[{'url':'https://edostavka.by/product/456'}])
    monkeypatch.setattr(provider,'fetch_product',lambda url:pytest.fail('Wrong source must not fetch'))
    assert run(tid)
    with database() as db:
        assert not db.get(CatalogOfferWatch,tid)
        assert db.get(CatalogOfferMatch,tid).state=='error'


def test_dashboard_names_unresolved_source_when_another_is_connected(client,monkeypatch):
    pid,tid=setup(client,monkeypatch);assert run(tid)
    client.put(f'/api/v1/catalog-watches/{pid}',json={'enabled':True})
    changed=client.patch(f'/api/v1/operations/catalog-products/{pid}',json={'codes':{'retailers':[{'shop_name':'Е-доставка','retailer_code':'456'}]}})
    assert changed.status_code==200,changed.text
    dashboard=client.get('/api/v1/catalog-watches').json()
    assert len(dashboard['offers'])==1
    assert dashboard['unlinked'][0]['matching_sources']==['Е-доставка']


def test_edostavka_article_autolinks_unavailable_product_missing_from_search(client,monkeypatch):
    import httpx
    from tests.api.test_catalog_watch_api import document
    p=create(client,codes={'barcodes':[{'codes':[CODE]}],'retailers':[{'shop_name':'Евроопт','retailer_code':'870666'}]}).json()
    pid,tid=p['id'],p['offers'][0]['id']
    real=httpx.Client;paths=[]
    def handler(request):
        paths.append(request.url.path)
        if request.url.path=='/search':
            return httpx.Response(200,text='<script id="__NEXT_DATA__">'+json.dumps({'page':'/search','props':{'pageProps':{'search':{'query':CODE,'productIds':[]},'listing':{'products':[]}}}})+'</script>')
        assert request.url.path=='/product/870666'
        return httpx.Response(200,text=document('0',False).replace('10.99','0'))
    monkeypatch.setattr(provider.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(handler),**kw))
    assert run(tid)
    with database() as db:
        w=db.get(CatalogOfferWatch,tid)
        assert w.url=='https://edostavka.by/product/870666' and w.snapshot['price'] is None
        assert db.get(CatalogOfferMatch,tid).state=='linked'
        assert not list(db.scalars(select(CatalogPriceEvent)))
    assert paths==['/search','/product/870666','/product/870666']
