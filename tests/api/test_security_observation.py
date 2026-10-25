import json
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request as StarletteRequest

from app.core.security_observation import (
    SecurityJournal, SecurityObserver, SIGNAL_PATHS, client_context, documentation_options,
)


def request(path='/api/v1/auth/admin/login', *, peer='192.0.2.1', headers=(), method='GET'):
    result = StarletteRequest({'type': 'http', 'method': method, 'path': path,
        'query_string': b'secret=should-not-appear', 'headers': headers,
        'client': (peer, 1234), 'server': ('test', 80), 'scheme': 'http'})
    result.state.request_id = 'server-generated-id'
    return result


def test_proxy_headers_only_trusted_from_explicit_peer():
    headers = [(b'x-real-ip', b'203.0.113.5'), (b'x-forwarded-for', b'203.0.113.99'),
               (b'x-fa-rate-observation', b'REJECTED_DRY_RUN')]
    assert client_context(request(headers=headers), frozenset()) == ('192.0.2.1', None)
    assert client_context(request(headers=headers), frozenset({'192.0.2.1'})) == ('203.0.113.5', 'REJECTED_DRY_RUN')
    assert client_context(request(headers=[(b'x-real-ip', b'bad\nIP')]), frozenset({'192.0.2.1'})) == ('192.0.2.1', None)


def test_signal_paths_keep_ordinary_404_and_no_secret_logging(monkeypatch):
    import app.main as main
    events = []
    monkeypatch.setattr(main, 'security_observer', SecurityObserver(events.append))
    client = TestClient(main.app)
    for path in sorted(SIGNAL_PATHS)[:8]:
        response = client.post(path + '?token=private', json={'password': 'private'},
            headers={'Authorization': 'Bearer private', 'X-Request-ID': 'private\nforged-event'})
        assert response.status_code == 404
        assert response.json() == {'detail': 'Not Found'}
        UUID(response.headers['X-Request-ID'])
    assert len(events) == 8
    assert 'private' not in json.dumps(events)
    assert all(event['user_id'] is None and event['mode'] == 'observe' for event in events)
    assert events[-1]['distinct_paths'] == 8
    client.get('/missing-ordinary-page')
    client.get('/static/missing-file.png')
    assert len(events) == 8


def test_failures_are_correlated_but_pending_denials_are_ignored():
    events = []
    observer = SecurityObserver(events.append)
    req = request('/api/v1/auth/telegram')
    for _ in range(4):
        observer.observe(req, 400)
    assert events == []

    observer.observe(req, 422)
    assert events[0]['event'] == 'repeated_access_failure'
    assert events[0]['failures_in_window'] == 5
    events.clear()
    observer = SecurityObserver(events.append)
    req.state.access_not_approved = True
    req.state.authenticated_user_id = 4
    for _ in range(30):
        observer.observe(req, 403)
    assert events == []


def test_login_attack_threshold_is_not_lost_to_minute_sampling():
    from app.services.security_alert_service import qualifies
    events=[]
    observer=SecurityObserver(events.append,clock=lambda:1)
    req=request('/api/v1/auth/telegram',method='POST')
    for _ in range(50):observer.observe(req,401)
    assert len([e for e in events if qualifies(e)])==1
    assert events[-1]['login_failures_in_window']==50
    events.clear()
    observer=SecurityObserver(events.append,clock=lambda:1)
    for _ in range(100):observer.observe(request('/api/v1/auth/refresh',method='POST'),401)
    assert not any(qualifies(e) for e in events)


def test_verified_identity_is_attached_only_by_auth_dependency(monkeypatch):
    from app.api.deps import get_current_user
    req = request()
    user = SimpleNamespace(id=123, status='approved')
    monkeypatch.setattr('app.api.deps.AuthContextService.resolve_user_from_authorization_header', lambda *args: user)
    assert get_current_user(authorization='Bearer verified', db=None, request=req) == user
    events = []
    SecurityObserver(events.append).observe(req, 404)
    assert events[0]['user_id'] == 123


def test_observation_never_changes_status_even_when_flooded(monkeypatch):
    import app.main as main
    events = []
    observer = SecurityObserver(events.append, trusted_proxy_ips={'testclient'})
    monkeypatch.setattr(main, 'security_observer', observer)
    with TestClient(main.app) as client:
        for _ in range(50):
            response = client.get('/api/v1/auth/admin/login', headers={
                'X-Real-IP': '192.0.2.3', 'X-FA-Rate-Observation': 'REJECTED_DRY_RUN'})
            assert response.status_code == 404
        assert client.get('/health').status_code == 200
    assert len(events) == 1
    assert events[0]['event'] == 'rate_would_limit'


def test_volume_memory_and_expiry_are_bounded():
    events, now = [], [0.0]
    observer = SecurityObserver(events.append, clock=lambda: now[0])
    for n in range(5000):
        observer.observe(request(peer=f'10.{n // 65536}.{n // 256 % 256}.{n % 256}'), 404)
    assert len(events) == observer.MAX_EVENTS_PER_MINUTE
    assert len(observer.sources) == observer.MAX_SOURCES
    now[0] = 301
    observer.observe(request(), 404)
    assert len(observer.sources) == 1
    assert len(events) == observer.MAX_EVENTS_PER_MINUTE + 1
    assert events[-1]['suppressed_since_last_event'] == 4800


def test_path_field_uses_route_template_not_user_data():
    events = []
    observer = SecurityObserver(events.append)
    req = request('/api/v1/operations/private-injected-id')
    req.scope['route'] = SimpleNamespace(path='/api/v1/operations/{operation_id}')
    for _ in range(5):
        observer.observe(req, 401)
    assert events[0]['path'] == '/api/v1/operations/{operation_id}'
    assert 'private-injected' not in json.dumps(events)


def test_storage_rotates_is_private_and_survives_reopening(tmp_path):
    path = tmp_path / 'private' / 'security.jsonl'
    journal = SecurityJournal(str(path))
    journal.handler.maxBytes = 160
    for n in range(30):
        journal({'event': 'signal_route', 'n': n, 'path': '/login'})
    journal.handler.close()
    assert len(list(path.parent.glob('security.jsonl*'))) == 4
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    reopened = SecurityJournal(str(path))
    reopened({'event': 'new'})
    reopened.handler.close()
    assert json.loads(path.read_text().splitlines()[-1]) == {'event': 'new'}
    for item in path.parent.iterdir():
        os.utime(item, (0, 0))
    expired = SecurityJournal(str(path))
    assert not list(path.parent.glob('security.jsonl*'))
    expired.handler.close()


def test_journal_reopens_after_another_writer_rotates(tmp_path):
    path = tmp_path / 'security.jsonl'
    first, second = SecurityJournal(str(path)), SecurityJournal(str(path))
    first.handler.maxBytes = second.handler.maxBytes = 100
    first({'event': 'initial'})
    for n in range(8):
        second({'event': 'rotating', 'n': n})
    first({'event': 'after_rotation'})
    assert json.loads(path.read_text().splitlines()[-1]) == {'event': 'after_rotation'}
    first.handler.close()
    second.handler.close()


def test_journal_failure_does_not_break_request():
    def broken(event):
        raise OSError('disk full')
    SecurityObserver(broken).observe(request(), 404)


@pytest.mark.parametrize('production', [True, False])
def test_docs_disabled_only_in_production(production):
    app = FastAPI(**documentation_options(production))
    client = TestClient(app)
    for path in ['/docs', '/redoc', '/openapi.json', '/docs/oauth2-redirect']:
        assert client.get(path).status_code == (404 if production else 200)


def test_deployment_config_is_observation_only():
    root = Path(__file__).resolve().parents[2]
    config = (root / 'deploy/nginx/financialassistant-observation-location.conf').read_text()
    assert 'limit_req_dry_run on;' in config
    assert 'limit_req_dry_run off' not in config
    assert 'X-FA-Rate-Observation $limit_req_status' in config
    compose = (root / 'docker-compose.yml').read_text()
    assert '--no-proxy-headers --no-access-log' in compose
    assert 'security_logs:/var/log/financialassistant' in compose


def test_source_sampling_and_failure_window_expire():
    events, now = [], [0.0]
    observer = SecurityObserver(events.append, clock=lambda: now[0])
    for path in SIGNAL_PATHS:
        observer.observe(request(path), 404)
    assert len(events) == 10
    now[0] = 61
    observer.observe(request(), 404)
    assert len(events) == 11
    assert events[-1]['suppressed_since_last_event'] == len(SIGNAL_PATHS) - 10
    events.clear()
    observer = SecurityObserver(events.append, clock=lambda: now[0])
    for _ in range(4):
        observer.observe(request('/api/v1/auth/telegram'), 400)
    now[0] += 301
    observer.observe(request('/api/v1/auth/telegram'), 400)
    assert not events


def test_spoofed_rate_header_does_not_create_an_event():
    events = []
    SecurityObserver(events.append).observe(request('/health', headers=[
        (b'x-real-ip', b'203.0.113.5'), (b'x-fa-rate-observation', b'REJECTED_DRY_RUN')]), 200)
    assert events == []


def test_histogram_counts_login_failures_before_sampling_and_resets_with_window():
    events=[];now=[1.0]
    observer=SecurityObserver(events.append,clock=lambda:now[0])
    req=request('/api/v1/auth/telegram',method='POST')
    for minute,count in enumerate([8,11,9,15,13]):
        now[0]=1.0+60*minute
        for _ in range(count):observer.observe(req,401)
    # A threshold crossing emits a snapshot even when other events were sampled.
    snapshot=next(e for e in events if e['login_failures_in_window']>=50)
    assert snapshot['login_failure_buckets']==[8,11,9,15,7]
    assert sum(snapshot['login_failure_buckets'])==50
    assert observer.sources['192.0.2.1'].login_failure_buckets==[8,11,9,15,13]
    for _ in range(30):observer.observe(request('/api/v1/auth/refresh',method='POST'),401)
    assert observer.sources['192.0.2.1'].login_failure_buckets==[8,11,9,15,13]
    now[0]=302
    for _ in range(50):observer.observe(req,401)
    assert events[-1]['login_failure_buckets']==[50]
