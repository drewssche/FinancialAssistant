import base64
import io

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
