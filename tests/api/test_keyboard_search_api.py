"""User-visible search parity, pagination and tenant boundaries."""
import pytest

from app.api.deps import get_current_user_id
from app.core.cache import reset_cache_for_tests
from app.db.models import User
from app.db.session import get_db
from app.main import app
from tests.api.test_operations_api import _client_lifecycle


@pytest.fixture
def client():
    yield from _client_lifecycle()


def post(client, path, payload):
    response = client.post('/api/v1/' + path, json=payload)
    assert response.status_code in (200, 201), response.text
    return response.json()


def get(client, path, **params):
    response = client.get('/api/v1/' + path, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_catalog_keyboard_rank_before_pagination_and_tenant_isolation(client):
    path = 'operations/catalog-products'
    corrected = post(client, path, {'name': 'МОЛОКО'})
    original = post(client, path, {'name': 'vjkjrj'})
    post(client, path, {'name': 'Чай'})
    # A separate user's exact and corrected hits must never affect count/pages.
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    db.add(User(id=2, display_name='Other', status='active'))
    db.commit()
    generator.close()
    app.dependency_overrides[get_current_user_id] = lambda: 2
    post(client, path, {'name': 'Молоко чужое'})
    post(client, path, {'name': 'vjkjrj чужое'})
    app.dependency_overrides[get_current_user_id] = lambda: 1
    for page, expected in [(1, original), (2, corrected)]:
        payload = get(client, path, q='vjkjrj', page=page, page_size=1)
        assert payload['total'] == 2
        assert [item['id'] for item in payload['items']] == [expected['id']]
    assert get(client, path, q='vjkjrj', page=3, page_size=1)['items'] == []


def test_catalog_searches_related_source_brand_category_and_offer(client):
    source = post(client, 'operations/item-sources', {'name': 'Соседи'})
    brand = post(client, 'operations/item-brands', {'name': 'Зелёный'})
    category = post(client, 'categories', {'name': 'Напитки', 'kind': 'expense'})
    product = post(client, 'operations/catalog-products', {
        'name': 'Продукт', 'brand_id': brand['id'], 'category_id': category['id'],
    })
    offer = post(client, 'operations/item-templates', {
        'name': 'Молоко', 'source_id': source['id'], 'product_id': product['id'],
        'latest_unit_price': '2.00',
    })
    for query in ['cjctlb', 'зЕЛЕНЫЙ', 'yfgbnrb', 'vjkjrj']:
        result = get(client, 'operations/catalog-products', q=query)
        assert [row['id'] for row in result['items']] == [product['id']], query
    for path, query, expected in [('item-sources', 'cjctlb', source), ('item-brands', 'ptktysq', brand), ('item-templates', 'vjkjrj', offer)]:
        rows = get(client, 'operations/' + path, q=query)['items']
        assert [row['id'] for row in rows] == [expected['id']]
    assert get(client, 'operations/catalog-products', q='vjkjrj', brand_id=brand['id'] + 999)['total'] == 0


@pytest.mark.parametrize('path', ['operations', 'operations/money-flow'])
def test_operations_keyboard_note_kind_receipt_and_filters(client, path):
    first = post(client, 'operations', {'kind': 'expense', 'amount': '10', 'operation_date': '2026-03-01', 'note': 'Молоко'})
    second = post(client, 'operations', {'kind': 'expense', 'amount': '20', 'operation_date': '2026-03-02', 'note': 'vjkjrj'})
    post(client, 'operations', {'kind': 'income', 'amount': '30', 'operation_date': '2026-03-03', 'note': 'Зарплата'})
    for page, expected in [(1, second), (2, first)]:
        data = get(client, path, q='vjkjrj', page=page, page_size=1)
        assert data['total'] == 2
        assert data['items'][0].get('source_id', data['items'][0]['id']) == expected['id']
    assert get(client, path, q='hfc[jl')['total'] == 2
    assert get(client, path, q='vjkjrj', date_from='2026-03-02')['total'] == 1
    receipt = post(client, 'operations', {'kind': 'expense', 'operation_date': '2026-03-04', 'receipt_items': [
        {'name': 'Печенье', 'shop_name': 'Магазин', 'quantity': '2', 'unit_price': '3'},
    ]})
    result = get(client, path, q='gtxtymt')
    assert result['total'] == 1
    assert result['items'][0].get('source_id', result['items'][0]['id']) == receipt['id']


def test_search_literal_wildcards_and_normalization(client):
    path = 'operations/catalog-products'
    special = post(client, path, {'name': 'Сыр 50%_\\'})
    post(client, path, {'name': 'Сыр 50 обычный'})
    for query in ['%', '_', '\\']:
        assert [row['id'] for row in get(client, path, q=query)['items']] == [special['id']]
    tea = post(client, path, {'name': 'ЗелЁный чай'})
    assert get(client, path, q='  зеленый   ЧАЙ  ')['items'][0]['id'] == tea['id']
    assert get(client, path, q='   ')['total'] == 3


def test_plans_history_debts_and_categories(client):
    category = post(client, 'categories', {'name': 'Ремонт', 'kind': 'expense'})
    plan = post(client, 'plans', {'kind': 'expense', 'amount': '10', 'scheduled_date': '2026-03-01', 'note': 'Молоко', 'category_id': category['id']})
    assert get(client, 'plans', q='vjkjrj')['items'][0]['id'] == plan['id']
    assert get(client, 'plans', q='htvjyn')['total'] == 1
    post(client, f"plans/{plan['id']}/confirm", {})
    assert get(client, 'plans/history', q='vjkjrj')['total'] == 1
    post(client, 'debts', {'counterparty': 'Иван', 'direction': 'lend', 'principal': '50', 'start_date': '2026-03-01', 'note': 'Ремонт'})
    for query in ['bdfy', 'htvjyn']:
        reset_cache_for_tests()
        assert get(client, 'debts/cards', q=query)[0]['counterparty'] == 'Иван'
    assert get(client, 'categories', q='htvjyn', page=1, page_size=20)['items'][0]['id'] == category['id']


def test_work_payment_candidates_keyboard_and_date_filter(client):
    operation = post(client, 'operations', {'kind': 'income', 'amount': '100', 'operation_date': '2026-03-01', 'note': 'Премия'})
    post(client, 'operations', {'kind': 'expense', 'amount': '10', 'operation_date': '2026-03-01', 'note': 'Премия'})
    data = get(client, 'work/payments/candidates', q='ghtvbz', date_from='2026-03-01', date_to='2026-03-31')
    assert data['total'] == 1
    assert data['items'][0]['operation_id'] == operation['id']
    assert get(client, 'work/payments/candidates', q='ghtvbz', date_from='2026-04-01', date_to='2026-04-30')['total'] == 0
