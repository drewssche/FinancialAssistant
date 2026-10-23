import pytest
from app.api.deps import get_current_user_id
from app.main import app
from app.services import receipt_site_service as site
from tests.api.test_catalog_product_linkage_api import client, _source
from tests.api.test_receipt_codes_api import receipt

CODE = '4811040140757'
CODES = [{'kind': 'barcode', 'code': CODE}, {'kind': 'retailer', 'code': '2186323'}]
URL = 'https://edostavka.by/product/2186323'


@pytest.fixture(autouse=True)
def retailer(monkeypatch):
    site.discover.cache_clear()
    monkeypatch.setattr(site.provider, 'search_products', lambda key, query, kind: [{'url': URL}])
    monkeypatch.setattr(site.provider, 'fetch_product', lambda url: {
        'url': url, 'name': 'Пельмени 430 г', 'price': '99.00', 'unit': 'шт.',
        'identifiers': {'article': '2186323', 'barcodes': [CODE]}})
    yield
    site.discover.cache_clear()


def lookup(client, **extra):
    return client.post('/api/v1/operations/catalog-products/lookup-site-codes', json={
        'codes': CODES, 'shop_name': 'Евроопт', **extra})


def test_preview_read_only_and_save_atomic_without_changing_receipt_price(client):
    result = lookup(client)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['auto_match'] and len(data['items']) == 1
    assert client.get('/api/v1/operations/catalog-products').json()['total'] == 0
    token = data['items'][0]['site_selection']
    response = receipt(client, CODES, shop_name='Евроопт', site_selection=token)
    assert response.status_code == 201, response.text
    operation = response.json(); row = operation['receipt_items'][0]
    assert operation['receipt_total'] == '6.20' and row['unit_price'] == '3.10'
    identity = client.get(f"/api/v1/operations/catalog-products/{row['product_id']}/identity").json()
    assert identity['offers'][0]['product_url'] == URL
    watch = client.get(f"/api/v1/catalog-watches/{row['product_id']}").json()
    assert watch['offers'][0]['snapshot'] == {}
    # Repeated saving remains idempotent and does not duplicate website links.
    result = receipt(client, CODES, shop_name='Евроопт', site_selection=token)
    assert result.status_code == 201, result.text
    assert result.json()['receipt_total'] == '6.20'


@pytest.mark.parametrize('change', ['source', 'codes', 'tamper', 'owner'])
def test_selection_context_and_signature_reject_without_partial_save(client, change):
    token = lookup(client).json()['items'][0]['site_selection']
    codes = CODES; shop = 'Евроопт'
    if change == 'source': shop = 'Green'
    if change == 'codes': codes = CODES[:1]
    if change == 'tamper': token = token[:-12] + 'xxxxxxxxxxxx'
    if change == 'owner': app.dependency_overrides[get_current_user_id] = lambda: 2
    response = receipt(client, codes, shop_name=shop, site_selection=token)
    assert response.status_code == 400, response.text
    assert client.get('/api/v1/operations').json()['total'] == 0
    assert client.get('/api/v1/operations/catalog-products').json()['total'] == 0


def test_multiple_exact_candidates_require_choice(client, monkeypatch):
    monkeypatch.setattr(site.provider, 'search_products', lambda *args: [{'url': URL}, {'url': 'https://edostavka.by/product/42'}])
    result = lookup(client).json()
    assert not result['auto_match'] and len(result['items']) == 2


def test_conflicting_barcode_even_with_matching_article_never_selected(client, monkeypatch):
    monkeypatch.setattr(site.provider, 'fetch_product', lambda url: {'url': url, 'name': 'Другой', 'identifiers': {'article': '2186323', 'barcodes': ['4810729017151']}})
    assert lookup(client).json()['items'] == []


def test_unavailable_and_unsupported_sites_do_not_block_receipt(client, monkeypatch):
    def fail(*args): raise site.provider.RetailerUnavailable('unavailable')
    monkeypatch.setattr(site.provider, 'search_products', fail)
    assert lookup(client).json()['state'] == 'unavailable'
    assert lookup(client, shop_name='Маяк').json()['state'] == 'unsupported'
    assert receipt(client, CODES, shop_name='Евроопт').status_code == 201


@pytest.mark.parametrize('name', ['Либретик', 'Либретек', 'ООО «Либретик»'])
def test_alias_reuses_sosedi_source_and_search_provider(client, monkeypatch, name):
    source_id = _source(client, 'Соседи'); calls = []
    monkeypatch.setattr(site.provider, 'search_products', lambda key, query, kind: calls.append(key) or [])
    assert lookup(client, shop_name=name).status_code == 200
    assert calls and set(calls) == {'sosedi'}
    response = receipt(client, CODES, shop_name=name)
    assert response.status_code == 201, response.text
    assert response.json()['receipt_items'][0]['source_id'] == source_id
    assert response.json()['receipt_items'][0]['shop_name'] == 'Соседи'
    sources = client.get('/api/v1/operations/item-sources').json()['items']
    assert [s['name'] for s in sources] == ['Соседи']


def test_other_users_source_not_queried(client, monkeypatch):
    source_id = _source(client, 'Соседи')
    app.dependency_overrides[get_current_user_id] = lambda: 2
    monkeypatch.setattr(site.provider, 'search_products', lambda *args: pytest.fail('must not fetch'))
    assert lookup(client, source_id=source_id).status_code == 404


@pytest.mark.parametrize('shop,key,url', [
    ('Green','green','https://green-dostavka.by/product/pelmeni-2186323/'),
    ('Соседи','sosedi','https://sosedi-dostavka.by/products/pelmeni-2186323'),
])
def test_selected_retailer_is_used_and_link_saved_for_both_networks(client,monkeypatch,shop,key,url):
    calls=[]
    monkeypatch.setattr(site.provider,'search_products',lambda actual_key,query,kind:calls.append(actual_key) or [{'url':url}])
    data=lookup(client,shop_name=shop).json()
    assert data['auto_match'] and set(calls)=={key}
    response=receipt(client,CODES,shop_name=shop,site_selection=data['items'][0]['site_selection'])
    assert response.status_code==201,response.text
    assert response.json()['receipt_total']=='6.20'
    row=response.json()['receipt_items'][0]
    identity=client.get(f"/api/v1/operations/catalog-products/{row['product_id']}/identity").json()
    assert identity['offers'][0]['product_url']==url


def test_changed_article_prevents_silent_link_even_when_barcode_matches(client):
    data=lookup(client,codes=[CODES[0],{'kind':'retailer','code':'different-article'}]).json()
    assert len(data['items'])==1 and not data['auto_match']


def test_restricted_internal_article_requires_manual_site_selection(client,monkeypatch):
    code='2237310222750'
    monkeypatch.setattr(site.provider,'fetch_product',lambda url:{'url':url,'name':'Лук красный','identifiers':{'article':code,'barcodes':[]}})
    result=lookup(client,codes=[{'kind':'retailer','code':code}])
    assert result.status_code==200,result.text
    assert len(result.json()['items'])==1 and not result.json()['auto_match']
