import json
import httpx
import pytest
from app.services import retailer_price_provider as provider
from tests.api.test_retailer_price_providers import mapping,green_data,green_html,sosedi_data,sosedi_html,SOSEDI


def green_search(query='123', kind='retailer'):
    p=provider.unpack(green_data()['product'])
    entry={**p['item'],'storeProduct':mapping(p['storeProduct'])}
    state={'search':mapping({'searchValue':query,'products':{'__iterable':'List','data':[mapping(entry)]}})}
    return '<script id="__NEXT_DATA__">'+json.dumps({'page':'/search','props':{'initialState':json.dumps(state)}})+'</script>'


def test_green_search_uses_requested_listing_and_exact_article():
    hit=provider.parse_green_search(green_search(),'123','retailer')[0]
    assert hit['article']=='123' and hit['price']=='2.99' and hit['available']
    assert provider.parse_green_search(green_search('12'),'12','retailer')==[]
    for html in ['bad',green_search('wrong'),green_search().replace('"/search"','"/"')]:
        with pytest.raises(ValueError):provider.parse_green_search(html,'123','retailer')


def test_sosedi_filters_fuzzy_codes_and_verifies_real_card(monkeypatch):
    calls=[];code='4810000000001'
    listing=json.dumps({'data':[{'id':456,'name':code+' Молоко'},{'id':789,'name':'4810000000002 Похожий товар'}]})
    monkeypatch.setattr(provider,'sosedi_product_index',lambda:{'456':SOSEDI})
    def read(url,params=None):
        calls.append((url,params))
        return listing if url.endswith('/search') else sosedi_html(sosedi_data())
    monkeypatch.setattr(provider,'read_public',read)
    hits=provider.search_products('sosedi',code,'barcode')
    assert len(hits)==1 and hits[0]['article']=='456' and hits[0]['price']=='2.99'
    assert len(calls)==2
    calls.clear();assert provider.search_products('sosedi','456','retailer')==hits
    assert calls==[(SOSEDI,None)]
    calls.clear();assert provider.search_products('sosedi','sku-other','retailer')==[] and not calls
    d=sosedi_data();d['product']['cod']='4810000000002'
    monkeypatch.setattr(provider,'read_public',lambda url,params=None: listing if url.endswith('/search') else sosedi_html(d))
    assert provider.search_products('sosedi',code,'barcode')==[]


@pytest.mark.parametrize('retailer',['green','sosedi'])
def test_fixed_search_origins_and_encoded_query(retailer,monkeypatch):
    real=httpx.Client;requests=[];q='a&query=b'
    def handler(request):
        requests.append(request)
        if retailer=='green':
            assert request.url.host=='green-dostavka.by' and request.url.params['search']==q
            return httpx.Response(200,text=green_search(q))
        assert request.url.host=='dev.bazar-store.by' and request.url.params['query']==q
        return httpx.Response(200,json={'data':[]})
    monkeypatch.setattr(provider.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(handler),**kw))
    provider.search_products(retailer,q)
    assert len(requests)==1
    for response in [httpx.Response(302,headers={'location':'http://127.0.0.1'}),httpx.Response(200,content=b'x'*3000001)]:
        monkeypatch.setattr(provider.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(lambda req:response),**kw))
        with pytest.raises(ValueError):provider.search_products(retailer,q)


def test_sitemap_accepts_only_fixed_product_urls(monkeypatch):
    import app.core.cache as cache
    saved=[]
    monkeypatch.setattr(cache,'get_json',lambda key:None)
    monkeypatch.setattr(cache,'set_json',lambda *args,**kw:saved.append(args))
    xml='<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+url+'</loc></url>' for url in [SOSEDI,'https://evil.test/products/x-123','https://sosedi-dostavka.by/categories/milk'])+'</urlset>'
    monkeypatch.setattr(provider,'read_public',lambda url:xml)
    assert provider.sosedi_product_index()=={'456':SOSEDI}
    assert saved
    monkeypatch.setattr(provider,'sosedi_product_index',lambda:{'456':'https://evil.test/products/x-456'})
    with pytest.raises(ValueError):provider.search_sosedi('456','retailer')


def test_edostavka_article_reads_exact_card_even_when_search_omits_it(monkeypatch):
    from tests.api.test_catalog_watch_api import document
    real=httpx.Client;requests=[]
    html=document('0',False).replace('10.99','0')
    def handler(request):
        requests.append(request)
        assert str(request.url)=='https://edostavka.by/product/870666'
        return httpx.Response(200,text=html)
    monkeypatch.setattr(provider.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(handler),**kw))
    hit=provider.search_products('edostavka','870666','retailer')[0]
    assert hit['article']=='870666' and hit['price'] is None and not hit['available']
    assert len(requests)==1
    for bad in ['https://evil.test','../123','12?x=1','000123']:
        assert provider.search_products('edostavka',bad,'retailer')==[]
    assert len(requests)==1
    for status in [404,410]:
        monkeypatch.setattr(provider.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(lambda req:httpx.Response(status)),**kw))
        assert provider.search_products('edostavka','870666','retailer')==[]
    for response in [httpx.Response(302,headers={'location':'http://127.0.0.1'}),httpx.Response(503),httpx.Response(200,text=html.replace('870666','870667'))]:
        monkeypatch.setattr(provider.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(lambda req:response),**kw))
        with pytest.raises(provider.RetailerUnavailable):provider.search_products('edostavka','870666','retailer')
