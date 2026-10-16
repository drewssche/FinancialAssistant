import json
import pytest
from app.api.deps import get_current_user_id
from app.main import app
from app.services import edostavka_provider as provider
from tests.api.test_catalog_product_linkage_api import client
from tests.api.test_product_primary_codes_api import create


def page(query='2186323', products=None, ids=None):
    p={'productId':2186323,'productName':'Пельмени 430 г','price':{'discountedPrice':6.71},'quantityInfo':{'measure':'шт'},'restInformation':{'isAvailable':True}}
    data={'page':'/search','props':{'pageProps':{'search':{'query':query,'productIds':[2186323] if ids is None else ids},'listing':{'products':[p] if products is None else products}}}}
    return '<script id="__NEXT_DATA__">'+json.dumps(data)+'</script>'


def test_parse_only_search_hits_and_never_claim_barcode_identity():
    hits=provider.parse_search(page(),'2186323')
    assert hits==[{'url':'https://edostavka.by/product/2186323','name':'Пельмени 430 г','price':'6.71','unit':'шт','available':True,'article':'2186323'}]
    assert provider.parse_search(page(ids=[]),'2186323')==[]
    for html in ['blocked',page(query='other'),page(products=[None]),page().replace('6.71','"NaN"')]:
        if 'NaN' in html:assert provider.parse_search(html,'2186323')==[]
        else:
            with pytest.raises(provider.RetailerUnavailable):provider.parse_search(html,'2186323')
    p=json.loads(page().split('>',1)[1].split('</')[0])['props']['pageProps']['listing']['products'][0]
    p['productId']='//evil.test';assert provider.parse_search(page(products=[p],ids=['//evil.test']),'2186323')==[]


def test_network_fixed_origin_encoded_query_and_bounded_response(monkeypatch):
    import httpx
    real=httpx.Client;requests=[]
    def handler(request):
        requests.append(request)
        assert request.url.host=='edostavka.by' and request.url.path=='/search'
        return httpx.Response(200,text=page(query=str(request.url.params['query'])))
    monkeypatch.setattr(provider.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(handler),**kw))
    provider.search_products('https://evil.test/?x=1&y=2')
    assert requests[0].url.params['query']=='https://evil.test/?x=1&y=2'
    for response in [httpx.Response(302,headers={'Location':'https://evil.test'}),httpx.Response(200,content=b'x'*3_000_001)]:
        monkeypatch.setattr(provider.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(lambda request:response),**kw))
        with pytest.raises(provider.RetailerUnavailable):provider.search_products('2186323')
    with pytest.raises(ValueError):provider.search_products('\n')


def test_search_owner_source_validation_dedup_and_no_link_write(client,monkeypatch):
    p=create(client,codes={'retailers':[{'shop_name':'Е-доставка','retailer_code':'2186323'}]}).json()
    pid=p['id'];tid=p['offers'][0]['id'];base=f'/api/v1/catalog-watches/{pid}'
    calls=[]
    def search(q):calls.append(q);return provider.parse_search(page(query=q),q)
    monkeypatch.setattr('app.api.v1.catalog_watch.search_products',search)
    payload={'codes':[{'kind':'barcode','code':'4811040140757'},{'kind':'retailer','code':'2186323'}]}
    r=client.post(base+f'/offers/{tid}/search',json=payload)
    assert r.status_code==200,r.text
    assert len(r.json()['items'])==1 and calls==['4811040140757','2186323']
    assert r.json()['items'][0]['match_kind']=='barcode'
    assert client.get(base).json()['offers']==[]
    assert client.post(base+f'/offers/{tid}/search',json={'name':'Пельмени'}).status_code==200
    for bad in [{},{'name':'Молоко','codes':payload['codes']},{'codes':[{'kind':'barcode','code':'123'}]},{'codes':payload['codes']*3}]:
        before=len(calls);assert client.post(base+f'/offers/{tid}/search',json=bad).status_code in (400,422);assert len(calls)==before
    before=len(calls)
    app.dependency_overrides[get_current_user_id]=lambda:2
    assert client.post(base+f'/offers/{tid}/search',json=payload).status_code==404
    assert len(calls)==before


def test_search_wrong_offer_and_source_never_fetch(client,monkeypatch):
    p=create(client,codes={'retailers':[{'shop_name':'Green','retailer_code':'123'}]}).json()
    monkeypatch.setattr('app.api.v1.catalog_watch.search_products',lambda q:pytest.fail('must validate before fetch'))
    payload={'codes':[{'kind':'retailer','code':'123'}]}
    base=f"/api/v1/catalog-watches/{p['id']}/offers/"
    assert client.post(base+str(p['offers'][0]['id'])+'/search',json=payload).status_code==400
    assert client.post(base+'999999/search',json=payload).status_code==404
