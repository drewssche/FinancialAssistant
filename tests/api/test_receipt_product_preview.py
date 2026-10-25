import json
from io import BytesIO

import httpx
import pytest
from PIL import Image
from jose import jwt

from app.services import receipt_product_preview as preview
from app.services import receipt_site_service as site
from tests.api.test_retailer_price_providers import green_data, green_html, GREEN, sosedi_data, sosedi_html, SOSEDI
from tests.api.test_catalog_watch_api import document, URL
from tests.api.test_retailer_search import green_search
from tests.api.test_receipt_site_codes_api import client, lookup, CODES
from tests.api import test_receipt_site_codes_api as site_tests


@pytest.fixture
def retailer(monkeypatch):
    yield from site_tests.retailer.__wrapped__(monkeypatch)


@pytest.mark.parametrize('url,build,html', [(GREEN,green_data,green_html),(SOSEDI,sosedi_data,sosedi_html)])
def test_identity_does_not_require_price_stock_or_store(url,build,html):
    data=build()
    if url==GREEN:
        data.pop('store')
        preview.retailer.unpack(data['product']).pop('storeProduct')
    else:
        data.pop('darkstore');data['product'].pop('price');data['product'].pop('qty')
    result=preview.parse_product(html(data),url)
    assert result['name']=='Молоко 900 мл' and result['identifiers']['barcodes']==['4810000000001']
    assert 'price' not in result
    with pytest.raises(ValueError):preview.parse_product(html(data),url.replace('moloko','wrong'))


def test_edostavka_identity_size_and_public_photo_without_price():
    html=document().replace('"price":', '"unused_price":').replace('"restInformation":', '"unused_stock":')
    html+='<meta property="og:image" content="https://cdn.ime.by/product.png">'
    result=preview.parse_product(html,URL)
    assert result['size_label']=='125 г' and result['image_url']=='https://cdn.ime.by/product.png'


def test_search_listings_do_not_require_prices(monkeypatch):
    monkeypatch.setattr(preview.retailer,'read_public',lambda *args:green_search().replace('priceWithSale','missing_price'))
    assert preview.search_products('green','123','retailer')==[{'url':GREEN}]
    monkeypatch.setattr(preview.retailer,'read_public',lambda *args:'<script id="__NEXT_DATA__">'+json.dumps({'page':'/search','props':{'pageProps':{'search':{'query':'code','productIds':[42,43]},'listing':{}}}})+'</script>')
    assert len(preview.search_products('edostavka','code','barcode'))==2


@pytest.mark.parametrize('url',['http://cdn.ime.by/x','https://cdn.ime.by.evil.test/x','https://localhost/x','https://127.0.0.1/x','https://user:pass@cdn.ime.by/x','https://cdn.ime.by:bad/x','https://cdn.ime.by:8443/x'])
def test_untrusted_image_is_not_fetched(url,monkeypatch):
    monkeypatch.setattr(httpx,'Client',lambda **kw:pytest.fail('must not fetch'))
    assert preview.safe_image_url(url,URL) is None
    with pytest.raises(ValueError):preview.thumbnail(url,0)


def test_thumbnail_is_bounded_and_reencoded_without_redirects(monkeypatch):
    buf=BytesIO();Image.new('RGB',(400,400)).save(buf,'PNG');real=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda **kw:real(**kw,transport=httpx.MockTransport(lambda r:httpx.Response(200,content=buf.getvalue()))))
    data=preview.thumbnail('https://cdn.ime.by/test.png',1)
    assert data.startswith('data:image/jpeg;base64,') and len(data)<20000
    monkeypatch.setattr(httpx,'Client',lambda **kw:real(**kw,transport=httpx.MockTransport(lambda r:httpx.Response(302,headers={'location':'http://127.0.0.1'}))))
    with pytest.raises(httpx.HTTPError):preview.thumbnail('https://cdn.ime.by/test.png',2)


def test_saved_link_precedes_site_search(monkeypatch):
    site.discover.cache_clear()
    monkeypatch.setattr(preview,'fetch_product',lambda url:{'url':URL,'name':'Сыр','identifiers':{'barcodes':[CODES[0]['code']]}})
    monkeypatch.setattr(preview,'search_products',lambda *args:pytest.fail('saved exact card should win'))
    found,partial=site.discover('edostavka',tuple(site.code_context(CODES[:1])),0,URL)
    assert len(found)==1 and not partial


def test_other_stores_are_reference_only_and_never_receive_articles(client,retailer,monkeypatch):
    calls=[]
    urls={'green':GREEN,'sosedi':SOSEDI}
    monkeypatch.setattr(preview,'search_products',lambda key,q,kind:calls.append((key,q,kind)) or [{'url':urls[key]}])
    monkeypatch.setattr(preview,'fetch_product',lambda url:{'url':url,'name':'Товар','source':'Другой магазин','identifiers':{'barcodes':[CODES[0]['code']]}})
    data=lookup(client,other_sources=True).json()
    assert len(data['items'])==2 and not data['auto_match']
    assert all(i['reference_only'] and i['site_selection'] is None for i in data['items'])
    assert all(kind=='barcode' for _,_,kind in calls)
    calls.clear()
    assert lookup(client,other_sources=True,codes=[CODES[1]]).json()['state']=='missing_codes'
    assert not calls


def test_thumbnail_token_is_bound_to_user_and_purpose(client,retailer,monkeypatch):
    monkeypatch.setattr(preview,'fetch_product',lambda url:{'url':url,'name':'Товар','image_url':'https://cdn.ime.by/x.png','identifiers':{'barcodes':[CODES[0]['code']]}})
    token=lookup(client).json()['items'][0]['image_token']
    monkeypatch.setattr(preview,'thumbnail',lambda *args:'data:image/jpeg;base64,test')
    assert client.post('/api/v1/operations/catalog-products/receipt-thumbnail',json={'token':token}).json()['image']
    claims=jwt.decode(token,site.signing_key(),algorithms=['HS256']);claims['user_id']=2
    wrong=jwt.encode(claims,site.signing_key(),algorithm='HS256')
    assert client.post('/api/v1/operations/catalog-products/receipt-thumbnail',json={'token':wrong}).json()=={'image':None}
    selection=lookup(client).json()['items'][0]['site_selection']
    assert client.post('/api/v1/operations/catalog-products/receipt-thumbnail',json={'token':selection}).json()=={'image':None}


def test_one_broken_candidate_does_not_hide_verified_card(monkeypatch):
    site.discover.cache_clear()
    monkeypatch.setattr(preview,'search_products',lambda *a:[{'url':URL},{'url':'https://edostavka.by/product/42'}])
    def fetch(url):
        if url!=URL:raise ValueError('changed markup')
        return {'url':url,'name':'Сыр','identifiers':{'barcodes':[CODES[0]['code']]}}
    monkeypatch.setattr(preview,'fetch_product',fetch)
    found,partial=site.discover('edostavka',tuple(site.code_context(CODES[:1])),0)
    assert len(found)==1 and partial


def test_missing_article_is_not_reported_as_site_outage(monkeypatch):
    site.discover.cache_clear()
    monkeypatch.setattr(preview,'search_products',lambda *a:[{'url':URL}])
    def missing(url):raise preview.ProductMissing('404')
    monkeypatch.setattr(preview,'fetch_product',missing)
    assert site.discover('edostavka',(('retailer','870666'),),0)==([],False)


def test_article_survives_failed_barcode_search(monkeypatch):
    site.discover.cache_clear()
    def search(key,q,kind):
        if kind=='barcode':raise ValueError('temporary search failure')
        return [{'url':URL}]
    monkeypatch.setattr(preview,'search_products',search)
    monkeypatch.setattr(preview,'fetch_product',lambda url:{'url':url,'name':'Сыр','identifiers':{'article':'870666','barcodes':[]}})
    found,partial=site.discover('edostavka',tuple(site.code_context([CODES[0],{'kind':'retailer','code':'870666'}])),0)
    assert found[0]['matched_by']=='retailer' and partial


@pytest.mark.parametrize('key,url,article',[('edostavka',URL,'870666'),('sosedi',SOSEDI,'456')])
def test_article_only_identity_is_exact_and_shop_scoped(monkeypatch,key,url,article):
    site.discover.cache_clear();calls=[]
    monkeypatch.setattr(preview,'search_products',lambda k,q,kind:calls.append((k,q,kind)) or [{'url':url}])
    monkeypatch.setattr(preview,'fetch_product',lambda u:{'url':u,'name':'Товар','identifiers':{'article':article,'barcodes':[]}})
    found,partial=site.discover(key,(('retailer',article),),0)
    assert found[0]['matched_by']=='retailer' and found[0]['matched_code']==article
    assert calls==[(key,article,'retailer')]


def test_green_structured_photo_brand_and_size_without_title_size():
    data=green_data();item=preview.retailer.unpack(data['product'])['item'];item['title']='Пюре';item['volume']='90г';item['brand']={'title':'Маленькое счастье'}
    html=green_html(data)+'<script type="application/ld+json">'+json.dumps({'@type':'Product','url':GREEN,'image':'https://io.activecloud.com/static-green-market/test.png'})+'</script>'
    result=preview.parse_product(html,GREEN)
    assert result['size_label']=='90г' and result['brand']=='Маленькое счастье'
    assert result['image_url']=='https://io.activecloud.com/static-green-market/test.png'


def test_sosedi_photo_uses_verified_product_path_only():
    data=sosedi_data();data['product'].update(img='images/575813.jpg',brand='Coca Cola')
    result=preview.parse_product(sosedi_html(data),SOSEDI)
    assert result['image_url']=='https://bazar-store.by/images/575813.jpg' and result['brand']=='Coca Cola'
    for value in ['https://127.0.0.1/x','images/../../admin.png','//evil.test/x.jpg']:
        data['product']['img']=value
        assert preview.parse_product(sosedi_html(data),SOSEDI)['image_url'] is None
