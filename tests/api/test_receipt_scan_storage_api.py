import base64
import io
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import select

from app.api.deps import get_current_user_id
from app.db.models.operation import Operation
from app.db.session import get_db
from app.main import app
from tests.api.test_catalog_product_linkage_api import client


def scan():
    output = io.BytesIO()
    Image.new('RGB', (1000, 1600), 'white').save(output, format='PNG')
    return {'image': base64.b64encode(output.getvalue()).decode(), 'original_text': 'Исходный чек',
            'text': 'Уточнённый чек', 'review': {'rows': [{'name': 'Молоко', 'quantity': 2}], 'date': '2026-10-18'}}


def create(client, attachment=None):
    response = client.post('/api/v1/operations', json={'kind': 'expense', 'amount': '8.50',
        'operation_date': '2026-10-18', 'receipt_scan': attachment})
    assert response.status_code == 201, response.text
    return response.json()


def test_scan_atomic_save_read_edit_and_photo_only_purge(client):
    operation = create(client, scan())
    ident = operation['id']
    assert operation['has_receipt_scan'] and 'receipt_scan_data' not in operation
    saved = client.get(f'/api/v1/operations/{ident}/receipt-scan').json()
    assert saved['original_text'] == 'Исходный чек'
    image = Image.open(io.BytesIO(base64.b64decode(saved['image'])))
    assert image.format == 'WEBP' and image.size == (1000, 1600)
    assert client.patch(f'/api/v1/operations/{ident}', json={'receipt_scan': saved}).status_code == 200
    assert client.get(f'/api/v1/operations/{ident}/receipt-scan').json()['image'] == saved['image']
    client.patch(f'/api/v1/operations/{ident}', json={'note': 'Мой комментарий'})
    assert client.get(f'/api/v1/operations/{ident}/receipt-scan').json() == saved
    stats = client.get('/api/v1/operations/receipt-photos/storage').json()
    assert stats == {'count': 1, 'bytes': saved['image_bytes']}
    result = client.delete('/api/v1/operations/receipt-photos/storage').json()
    assert result == {'deleted': 1, 'freed_bytes': stats['bytes']}
    after = client.get(f'/api/v1/operations/{ident}').json()
    assert after['has_receipt_scan'] and after['amount'] == operation['amount'] and after['note'] == 'Мой комментарий'
    data = client.get(f'/api/v1/operations/{ident}/receipt-scan').json()
    assert data['image'] is None and data['review'] == saved['review'] and data['text'] == saved['text']
    assert client.delete('/api/v1/operations/receipt-photos/storage').json()['deleted'] == 0


def test_attachment_owner_isolation_and_deferred_loading(client):
    operation = create(client, scan())
    app.dependency_overrides[get_current_user_id] = lambda: 2
    assert client.get(f"/api/v1/operations/{operation['id']}/receipt-scan").status_code == 404
    assert client.get('/api/v1/operations/receipt-photos/storage').json()['count'] == 0
    assert client.delete('/api/v1/operations/receipt-photos/storage').json()['deleted'] == 0
    app.dependency_overrides[get_current_user_id] = lambda: 1
    assert client.get('/api/v1/operations/receipt-photos/storage').json()['count'] == 1
    session = next(app.dependency_overrides[get_db]())
    item = session.scalar(select(Operation).where(Operation.id == operation['id']))
    assert 'receipt_scan_image' not in item.__dict__ and 'receipt_scan_data' not in item.__dict__
    session.close()


@pytest.mark.parametrize('bad', [dict(image='invalid'), dict(review={'rows': [{}] * 151}), dict(image=base64.b64encode(b'not an image').decode())])
def test_invalid_scan_does_not_save_financial_operation(client, bad):
    result = client.post('/api/v1/operations', json={'kind': 'expense', 'amount': 5, 'operation_date': '2026-10-18', 'receipt_scan': bad})
    assert result.status_code == 400
    assert client.get('/api/v1/operations').json()['total'] == 0


def test_failed_update_retains_original_photo(client):
    operation = create(client, scan())
    url = f"/api/v1/operations/{operation['id']}"
    before = client.get(url+'/receipt-scan').json()
    assert client.patch(url, json={'amount': 30, 'receipt_scan': {'image': 'bad'}}).status_code == 400
    assert client.get(url+'/receipt-scan').json() == before
    assert client.get(url).json()['amount'] == operation['amount']


def reviewed_expense():
    return {
        'kind': 'expense', 'operation_date': '2026-10-18', 'amount': '8.50', 'currency': 'BYN',
        'receipt_items': [{'name': 'Молоко', 'shop_name': 'Green', 'quantity': '2', 'unit_price': '4.25'}],
        'receipt_scan': scan(),
    }


def test_scan_replay_is_scoped_to_user_and_preserves_a_single_purchase(client):
    key = {'Idempotency-Key': str(uuid4())}
    payload = reviewed_expense()
    path = '/api/v1/operations'
    first = client.post(path, json=payload, headers=key)
    assert first.status_code == 201, first.text
    repeated = client.post(path, json=payload, headers=key)
    assert repeated.status_code == 201 and repeated.json() == first.json()
    assert client.post(path, headers=key, json={**payload, 'note': 'изменено'}).status_code == 409
    assert client.get(path).json()['total'] == 1
    app.dependency_overrides[get_current_user_id] = lambda: 2
    other = client.post(path, headers=key, json=payload)
    assert other.status_code == 201 and other.json()['id'] != first.json()['id']
    app.dependency_overrides[get_current_user_id] = lambda: 1
    assert client.delete(f"{path}/{first.json()['id']}").is_success
    assert client.post(path, headers=key, json=payload).status_code == 409
    assert client.get(path).json()['total'] == 0


def test_rejected_scan_rolls_back_the_request_and_can_be_corrected(client):
    headers = {'Idempotency-Key': str(uuid4())}
    payload = reviewed_expense()
    path = '/api/v1/operations'
    bad = client.post(path, headers=headers, json={**payload, 'amount': '100.00'})
    assert bad.status_code == 400
    corrected = client.post(path, headers=headers, json=payload)
    assert corrected.status_code == 201, corrected.text
    another = client.post(path, headers={'Idempotency-Key': str(uuid4())}, json=payload)
    assert another.status_code == 201 and another.json()['id'] != corrected.json()['id']
