import re
from types import SimpleNamespace
import pytest
from app.api.deps import get_current_user
from app.db.models import User, AuthIdentity
from app.main import app
from tests.api.test_operations_api import client


@pytest.mark.parametrize('status',['approved','active','pending','rejected'])
def test_every_work_endpoint_rejects_non_admin_before_service(client,monkeypatch,status):
    monkeypatch.setattr('app.api.deps.get_settings',lambda:SimpleNamespace(admin_telegram_id_set={'900'}))
    user=User(id=1,status=status,identities=[AuthIdentity(provider='telegram',provider_user_id='901')])
    app.dependency_overrides[get_current_user]=lambda:user
    routes=[r for r in app.routes if getattr(r,'path','').startswith('/api/v1/work/')]
    assert len(routes)>=10
    for route in routes:
        path=re.sub(r'\{[^}]+\}','1',route.path)
        for method in route.methods:
            response=client.request(method,path,json={} if method in ('PUT','POST','PATCH') else None)
            assert response.status_code==403,(method,path,response.text)
            assert response.json()['detail']=='Admin access required'


def test_work_uses_same_configured_admin_identity_and_requires_auth(client,monkeypatch):
    monkeypatch.setattr('app.api.deps.get_settings',lambda:SimpleNamespace(admin_telegram_id_set={'900'}))
    assert client.get('/api/v1/work/profile').status_code==401
    admin=User(id=1,status='approved',identities=[AuthIdentity(provider='telegram',provider_user_id='900')])
    app.dependency_overrides[get_current_user]=lambda:admin
    assert client.get('/api/v1/work/profile').status_code==200
    assert client.put('/api/v1/work/profile',json={'company':'Admin company'}).status_code==200
    admin.identities=[]
    assert client.get('/api/v1/work/profile').status_code==403
