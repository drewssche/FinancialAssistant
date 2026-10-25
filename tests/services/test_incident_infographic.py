from io import BytesIO
from types import SimpleNamespace

import httpx
from PIL import Image
import pytest

from app.services.incident_infographic import render_notification, SIZE
from app.services.security_alert_service import SecurityAlerts, summarize, merge
from tests.services.test_security_alert_service import settings, event

NOW = 1792920000.0


def payload():
    return summarize(event(login_failures_in_window=56,login_failure_buckets=[8,11,9,15,13]), NOW)


def test_window_snapshots_are_not_summed_and_keep_histogram_on_retry():
    first = payload()
    last = summarize(event(login_failures_in_window=57,login_failure_buckets=[8,11,9,15,14]), NOW+1)
    result = merge(first, last)
    assert result['samples'] == 2
    assert result['login_snapshot']['count'] == 57
    assert sum(result['login_snapshot']['buckets']) == 57
    assert merge(result, first)['login_snapshot'] == result['login_snapshot']
    assert merge(result, summarize(event(client_ip='192.0.2.2'), NOW+2))['login_snapshot']['source'] == '192.0.2.1'


def test_missing_or_inconsistent_histogram_is_not_fabricated():
    data=summarize(event(login_failure_buckets=[50,50]),NOW)
    assert data['login_snapshot']['buckets'] == []
    data.pop('login_snapshot')
    png,caption=render_notification(data)
    assert 'Не менее 50' in caption
    assert png.startswith(b'\x89PNG')


@pytest.mark.parametrize('data',[
    payload(),
    summarize({'event':'security_notification_test'},NOW),
    {'operations':[{'issue':'bot','active':1,'reason':'bot_unhealthy','since':NOW-600,'changed':NOW,'last_seen':NOW+60}]},
    {'operations':[{'issue':'backup','active':1,'reason':'backup_unknown','since':NOW-72*3600,'changed':NOW},
                   {'issue':'bot','active':1,'reason':'bot_restarts','since':NOW-600,'changed':NOW}]},
])
def test_images_have_mobile_dimensions_bounded_size_and_real_captions(data):
    png,caption=render_notification(data)
    assert Image.open(BytesIO(png)).size == SIZE
    assert len(png) < 5_000_000 and len(caption) <= 1000
    assert 'ДЕМО' not in caption and '192.0.2.18' not in caption
    if data.get('kinds') == ['security_notification_test']:
        assert 'реального инцидента нет' in caption
    if data.get('login_snapshot'):
        assert '56' in caption and 'взлома' in caption


def capture_telegram(monkeypatch, response=None, fail=False):
    calls=[]
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            calls.append((url,kwargs))
            if fail: raise httpx.ReadTimeout('uncertain')
            return SimpleNamespace(raise_for_status=lambda:None,json=lambda:response or {'ok':True,'result':{'photo':[{'file_id':'test'}]}})
    monkeypatch.setattr('app.services.security_alert_service.httpx.Client',Client)
    return calls


def test_telegram_sends_one_photo_not_text_and_audits_acceptance(monkeypatch,tmp_path):
    calls=capture_telegram(monkeypatch);audit=[]
    a=SecurityAlerts(settings(tmp_path),audit.append)
    a.send_notification('telegram:123','Detailed body',payload())
    assert len(calls)==1 and calls[0][0].endswith('/sendPhoto')
    args=calls[0][1]
    assert args['files']['photo'][1].startswith(b'\x89PNG')
    assert '56' in args['data']['caption']
    assert audit[-1]['media']=='photo'


def test_render_failure_falls_back_before_network_and_keeps_details(monkeypatch,tmp_path):
    calls=capture_telegram(monkeypatch);audit=[]
    def broken(_):raise OSError('private font path')
    monkeypatch.setattr('app.services.incident_infographic.render_notification',broken)
    SecurityAlerts(settings(tmp_path),audit.append).send_notification('telegram:123','Detailed body',payload())
    assert len(calls)==1 and calls[0][0].endswith('/sendMessage')
    assert calls[0][1]['json']['text']=='Detailed body'
    assert audit[0]['event']=='notification_image_failed'
    assert 'private' not in str(audit)


def test_photo_timeout_never_triggers_additional_text_message(monkeypatch,tmp_path):
    calls=capture_telegram(monkeypatch,fail=True)
    with pytest.raises(httpx.ReadTimeout):
        SecurityAlerts(settings(tmp_path),lambda e:None).send_notification('telegram:123','text',payload())
    assert len(calls)==1 and calls[0][0].endswith('/sendPhoto')


def test_email_inlines_png_keeps_plain_text_and_escapes_html(monkeypatch,tmp_path):
    messages=[]
    class SMTP:
        def __init__(self,*args,**kwargs):assert kwargs['context']
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def login(self,*args):pass
        def send_message(self,message):messages.append(message);return {}
    monkeypatch.setattr('app.services.security_alert_service.smtplib.SMTP_SSL',SMTP)
    SecurityAlerts(settings(tmp_path),lambda e:None).send_notification('email','Title\n<script>untrusted</script>',payload())
    assert len(messages)==1
    message=messages[0]
    assert message['To']=='owner@example.org'
    assert '<script>' in message.get_body(preferencelist=('plain',)).get_content()
    html=message.get_body(preferencelist=('html',)).get_content()
    assert '<script>' not in html and '&lt;script&gt;' in html
    image=next(p for p in message.walk() if p.get_content_type()=='image/png')
    assert image['Content-Disposition']=='inline'
    assert 'cid:'+image['Content-ID'][1:-1] in html
    assert Image.open(BytesIO(image.get_payload(decode=True))).size==SIZE


def test_upgrade_preserves_quotas_pending_and_delivered_incidents(tmp_path):
    a=SecurityAlerts(settings(tmp_path),lambda e:None,clock=lambda:NOW,send=lambda *args:None)
    a.record(event());a.tick(force_batch=True)
    with a.connect() as db:
        before=[tuple(r) for r in db.execute('SELECT * FROM channels ORDER BY channel')]
    a=SecurityAlerts(settings(tmp_path),lambda e:None,clock=lambda:NOW+61,send=lambda *args:pytest.fail('duplicate'))
    a.record(event());a.tick(force_batch=True)
    with a.connect() as db:
        assert [tuple(r) for r in db.execute('SELECT * FROM channels ORDER BY channel')]==before
