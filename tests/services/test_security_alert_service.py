import json
from types import SimpleNamespace

from app.services.security_alert_service import SecurityAlerts, DAILY_LIMIT, build_text


def settings(tmp_path):
    return SimpleNamespace(security_event_log_path=str(tmp_path / 'security.jsonl'),
        admin_telegram_id_set={'123'}, security_alert_email='owner@example.org',
        telegram_bot_token='token-secret', smtp_host='smtp.example.org', smtp_from='sender@example.org',
        smtp_username='sender', smtp_password='smtp-secret', smtp_port=465, smtp_security='ssl')


def event(**fields):
    return {'event': 'repeated_access_failure', 'client_ip': '192.0.2.1',
        'path': '/api/v1/auth/telegram', 'signals_in_window': 5, **fields}


def test_digest_waits_coalesces_and_survives_restart(tmp_path):
    now, audit, sends = [1792776000.0], [], []
    args = dict(clock=lambda: now[0], send=lambda *args: sends.append(args))
    alerts = SecurityAlerts(settings(tmp_path), audit.append, **args)
    for _ in range(20): alerts.record(event())
    alerts.tick()
    assert not sends
    alerts = SecurityAlerts(settings(tmp_path), audit.append, **args)
    now[0] += 901
    alerts.tick()
    assert len(sends) == 2
    assert all('Записей наблюдения: 20' in text for _, text in sends)
    alerts.tick()
    assert len(sends) == 2
    assert sum(e['event'] == 'security_notification_sent' for e in audit) == 2


def test_single_probe_is_quiet_and_sources_bounded(tmp_path):
    alerts = SecurityAlerts(settings(tmp_path), lambda e: None)
    alerts.record(event(event='signal_route', signals_in_window=1, distinct_paths=1))
    with alerts.connect() as db:
        assert all(row['pending'] is None for row in db.execute('SELECT pending FROM channels'))
    for n in range(200): alerts.record(event(client_ip=f'192.0.2.{n}', path=f'/known/{n}'))
    with alerts.connect() as db:
        payload = json.loads(db.execute('SELECT pending FROM channels LIMIT 1').fetchone()[0])
    assert len(payload['sources']) == len(payload['paths']) == 10


def test_cooldown_and_daily_caps_persist(tmp_path):
    now, sends = [1792717200.0], [] # midnight Minsk
    s = settings(tmp_path)
    for n in range(10):
        alerts = SecurityAlerts(s, lambda e: None, clock=lambda: now[0], send=lambda *args: sends.append(args))
        alerts.record(event())
        now[0] += 901
        alerts.tick()
        now[0] += 2699
    assert len(sends) == DAILY_LIMIT * 2
    now[0] = 1792717200.0 + 86401
    alerts.tick()
    assert len(sends) == (DAILY_LIMIT + 1) * 2


def test_channel_failure_does_not_repeat_success_or_expose_secrets(tmp_path):
    now, sends, audit = [1792776000.0], [], []
    def send(channel, text):
        sends.append(channel)
        if channel == 'email': raise RuntimeError('smtp-secret token-secret')
    alerts = SecurityAlerts(settings(tmp_path), audit.append, clock=lambda: now[0], send=send)
    alerts.record(event())
    now[0] += 901
    alerts.tick()
    for _ in range(3):
        now[0] += 3600
        alerts.tick()
    assert sends.count('telegram:123') == 1
    assert sends.count('email') == 3
    assert any(e['event'] == 'security_notification_abandoned' for e in audit)
    assert 'secret' not in json.dumps(audit)


def test_unconfigured_email_is_audited_without_claiming_delivery(tmp_path):
    now, audit, sends = [1792776000.0], [], []
    s = settings(tmp_path); s.smtp_password = ''
    alerts = SecurityAlerts(s, audit.append, clock=lambda: now[0], send=lambda channel, _: sends.append(channel))
    alerts.record(event()); now[0] += 901; alerts.tick(); alerts.tick()
    assert sends == ['telegram:123']
    assert sum(e['event'] == 'security_notification_unconfigured' for e in audit) == 1


def test_crash_outcome_is_reported_and_not_resent(tmp_path):
    audit, sends = [], []
    s = settings(tmp_path)
    alerts = SecurityAlerts(s, audit.append, send=lambda *args: sends.append(args))
    with alerts.connect() as db:
        db.execute('UPDATE channels SET inflight=? WHERE channel=?', ('{"id":"example"}', 'email'))
    alerts = SecurityAlerts(s, audit.append, send=lambda *args: sends.append(args))
    alerts.recover_uncertain(); alerts.tick()
    assert not sends
    assert audit[0]['event'] == 'security_notification_unknown_after_restart'


def test_access_changes_from_separate_process_are_journaled(tmp_path):
    audit = []
    app = SecurityAlerts(settings(tmp_path), audit.append)
    bot = SecurityAlerts(settings(tmp_path), lambda e: None)
    change = event(event='access_status_changed', user_id=1, target_user_id=4,
        previous_status='pending', next_status='rejected')
    bot.record(change)
    app.tick()
    assert audit == [change]
    app.tick()
    assert audit == [change]


def test_telegram_rejects_ok_false(monkeypatch, tmp_path):
    import pytest
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'ok': False})
    monkeypatch.setattr('app.services.security_alert_service.httpx.Client', Client)
    alerts = SecurityAlerts(settings(tmp_path), lambda e: None)
    with pytest.raises(RuntimeError): alerts.deliver('telegram:123', 'test')


def test_smtp_requires_tls_and_uses_fixed_recipient(monkeypatch, tmp_path):
    observed = []
    class SMTP:
        def __init__(self, host, port, **kwargs): observed.append(('connect', host, port, bool(kwargs.get('context'))))
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def login(self, user, password): observed.append(('login', user))
        def send_message(self, message): observed.append(('message', message['To'], message['From'])); return {}
    monkeypatch.setattr('app.services.security_alert_service.smtplib.SMTP_SSL', SMTP)
    SecurityAlerts(settings(tmp_path), lambda e: None).deliver('email', 'test')
    assert observed[0][-1] is True
    assert observed[-1] == ('message', 'owner@example.org', 'sender@example.org')
