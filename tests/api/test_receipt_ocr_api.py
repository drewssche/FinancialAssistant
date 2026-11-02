from types import SimpleNamespace
import httpx
import pytest
from app.api.v1 import receipt_ocr as api
from app.api.deps import get_current_user_id
from app.main import app
from tests.api.test_catalog_product_linkage_api import client


@pytest.fixture(autouse=True)
def runtime(monkeypatch):
    api.LAST_REQUEST.clear()
    monkeypatch.setattr(api,'get_settings',lambda:SimpleNamespace(receipt_ocr_url='http://receipt-ocr:8080'))


def remote(monkeypatch,code=200,data=None):
    class Remote:
        def __init__(self,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,*args,**kwargs):return httpx.Response(code,json=data or {})
        async def post(self,*args,**kwargs):return httpx.Response(code,json=data or {'text':'Текст чека'})
    monkeypatch.setattr(api.httpx,'AsyncClient',Remote)


def test_bridge_authentication_and_disabled_mode(client,monkeypatch):
    app.dependency_overrides.pop(get_current_user_id)
    assert client.post('/api/v1/receipt-ocr/recognize',content=b'photo').status_code==401
    app.dependency_overrides[get_current_user_id]=lambda:1
    monkeypatch.setattr(api,'get_settings',lambda:SimpleNamespace(receipt_ocr_url=''))
    assert client.get('/api/v1/receipt-ocr/status').json()=={'available':False}
    assert client.post('/api/v1/receipt-ocr/recognize',content=b'photo').status_code==503


def test_success_cooldown_busy_and_no_financial_writes(client,monkeypatch):
    remote(monkeypatch)
    assert client.get('/api/v1/receipt-ocr/status').json()=={'available':True}
    response=client.post('/api/v1/receipt-ocr/recognize',content=b'photo',headers={'Content-Type':'image/jpeg'})
    assert response.status_code==200 and response.json()['text']=='Текст чека'
    assert response.headers['cache-control']=='no-store'
    assert client.post('/api/v1/receipt-ocr/recognize',content=b'photo',headers={'Content-Type':'image/jpeg'}).status_code==429
    api.LAST_REQUEST.clear();api.SLOT.acquire()
    try:assert client.post('/api/v1/receipt-ocr/recognize',content=b'photo',headers={'Content-Type':'image/jpeg'}).status_code==429
    finally:api.SLOT.release()
    assert client.get('/api/v1/operations').json()['total']==0


@pytest.mark.parametrize('code',[400,413,429,504,500])
def test_worker_errors_leave_slot_available(client,monkeypatch,code):
    remote(monkeypatch,code)
    response=client.post('/api/v1/receipt-ocr/recognize',content=b'photo',headers={'Content-Type':'image/png'})
    assert response.status_code==(503 if code==500 else code)
    assert api.SLOT.acquire(blocking=False)
    api.SLOT.release()


def test_size_type_and_invalid_result(client,monkeypatch):
    assert client.post('/api/v1/receipt-ocr/recognize',content=b'x',headers={'Content-Type':'text/plain'}).status_code==415
    monkeypatch.setattr(api,'MAX_BYTES',2)
    assert client.post('/api/v1/receipt-ocr/recognize',content=b'xxx',headers={'Content-Type':'image/png'}).status_code==413
    api.LAST_REQUEST.clear();remote(monkeypatch,data={'text':123})
    assert client.post('/api/v1/receipt-ocr/recognize',content=b'x',headers={'Content-Type':'image/png'}).status_code==503
