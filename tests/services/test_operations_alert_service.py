import json
from types import SimpleNamespace
from app.services.security_alert_service import SecurityAlerts, DAILY_LIMIT
from app.services.operations_alert_service import observe


def harness(tmp_path, send=None):
    now, sent, audit = [1792800000.0], [], []
    settings = SimpleNamespace(security_event_log_path=str(tmp_path / 'security.jsonl'),
        admin_telegram_id_set={'123'}, security_alert_email='owner@example.org',
        telegram_bot_token='token', smtp_host='smtp.example.org', smtp_from='sender@example.org',
        smtp_username='sender', smtp_password='secret')
    alerts = SecurityAlerts(settings, audit.append, clock=lambda: now[0], send=send or (lambda *x: sent.append(x)))
    return alerts, now, sent, audit


def sample(alerts, *, backup='ok', healthy=True, restarts=0, identity='a'):
    observe(alerts, {'backup': backup, 'bot': {'id': identity, 'healthy': healthy, 'restarts': restarts}})


def advance(alerts, now, seconds, **kwargs):
    for _ in range(seconds // 60):
        now[0] += 60
        sample(alerts, **kwargs)
        alerts.tick()


def test_short_failure_and_unannounced_recovery_are_silent(tmp_path):
    a, now, sent, _ = harness(tmp_path)
    sample(a, healthy=False)
    advance(a, now, 540, healthy=False)
    advance(a, now, 3600)
    assert not sent


def test_persistent_outage_once_and_silent_recovery_survives_restart(tmp_path):
    a, now, sent, audit = harness(tmp_path)
    sample(a, healthy=False)
    advance(a, now, 600, healthy=False)
    assert len(sent) == 2
    a = SecurityAlerts(a.settings, audit.append, clock=lambda: now[0], send=lambda *x: sent.append(x))
    a.recover_uncertain()
    advance(a, now, 86400, healthy=False)
    assert len(sent) == 2
    advance(a, now, 360)
    assert len(sent) == 2
    assert any(e['event'] == 'operational_incident_recovered' for e in audit)
    advance(a, now, 3600)
    assert len(sent) == 2


def test_backup_and_bot_grouped_and_share_security_cooldown(tmp_path):
    a, now, sent, _ = harness(tmp_path)
    a.record({'event': 'security_notification_test'})
    a.tick(force_batch=True)
    sample(a, backup='unknown', healthy=False)
    advance(a, now, 1800, backup='unknown', healthy=False)
    assert len(sent) == 2
    advance(a, now, 1800, backup='unknown', healthy=False)
    assert len(sent) == 4
    assert 'Резервная копия' not in sent[-1][1] and 'Telegram-бот' in sent[-1][1]
    advance(a, now, 86400, backup='unknown', healthy=False)
    assert len(sent) == 4


def test_recovery_before_warning_delivery_is_suppressed(tmp_path):
    a, now, sent, _ = harness(tmp_path)
    a.record({'event': 'security_notification_test'})
    a.tick(force_batch=True)
    sample(a, healthy=False)
    advance(a, now, 600, healthy=False)
    advance(a, now, 3600)
    assert len(sent) == 2


def test_three_new_restarts_not_lifetime_count_trigger_once(tmp_path):
    a, now, sent, _ = harness(tmp_path)
    sample(a, restarts=6000)
    advance(a, now, 600, restarts=6000)
    assert not sent
    advance(a, now, 60, restarts=6003)
    advance(a, now, 600, restarts=6003)
    assert len(sent) == 2 and 'трёх перезапусков' in sent[-1][1]
    advance(a, now, 3600, restarts=6003)
    assert len(sent) == 2


def test_gap_does_not_prove_continuous_failure_and_stale_sample_cannot_send(tmp_path):
    a, now, sent, _ = harness(tmp_path)
    sample(a, healthy=False)
    now[0] += 3600
    sample(a, healthy=False)
    a.tick()
    assert not sent
    advance(a, now, 540, healthy=False)
    assert not sent
    now[0] += 60
    sample(a, healthy=False)
    now[0] += 181
    a.tick()
    assert not sent


def test_failed_channel_retries_bounded_without_repeating_success(tmp_path):
    attempts = []
    def send(channel, text):
        attempts.append(channel)
        if channel == 'email':
            raise ConnectionRefusedError('password-secret')
    a, now, _, audit = harness(tmp_path, send)
    sample(a, healthy=False)
    advance(a, now, 90000, healthy=False)
    assert attempts.count('telegram:123') == 1
    assert attempts.count('email') == 3
    assert 'password-secret' not in json.dumps(audit)
    advance(a, now, 3600)
    assert attempts.count('telegram:123') == 1
    assert attempts.count('email') == 3 # no recovery for a channel that never received warning


def test_unknown_delivery_after_crash_not_replayed(tmp_path):
    a, now, sent, _ = harness(tmp_path)
    sample(a, healthy=False)
    for _ in range(11):
        now[0] += 60
        sample(a, healthy=False)
    with a.connect() as db:
        db.execute('UPDATE channels SET inflight=?', (json.dumps({'id': 'unknown', 'operations': [{'issue': 'bot', 'active': 1}]}),))
    a.recover_uncertain()
    a.tick()
    assert not sent


def test_daily_quota_already_used_by_security_blocks_operations(tmp_path):
    a, now, sent, _ = harness(tmp_path)
    from datetime import datetime
    from zoneinfo import ZoneInfo
    day = datetime.fromtimestamp(now[0], ZoneInfo('Europe/Minsk')).date().isoformat()
    with a.connect() as db:
        db.execute('UPDATE channels SET day=?,attempts=?', (day, DAILY_LIMIT))
    sample(a, healthy=False)
    advance(a, now, 1800, healthy=False)
    assert not sent


def test_recent_backup_job_failures_are_quiet_and_missing_copy_needs_three_days(tmp_path):
    a,now,sent,_=harness(tmp_path)
    for status in ['failed','retention','unknown']:
        advance(a,now,1800,backup=status)
    assert not sent
    # Model 72 hours of continuous observations without waiting in real time.
    with a.connect() as db:
        db.execute("UPDATE operational_state SET since=? WHERE issue='backup'", (now[0]-72*3600+60,))
    advance(a,now,60,backup='unknown')
    assert len(sent)==2 and 'Резервная копия' in sent[-1][1]
    advance(a,now,600)
    assert len(sent)==2


def test_ambiguous_smtp_disconnect_never_replays_even_after_restart(tmp_path):
    import smtplib
    calls=[]
    def send(channel,text):
        calls.append(channel)
        if channel=='email':raise smtplib.SMTPServerDisconnected('possibly accepted')
    a,now,_,audit=harness(tmp_path,send)
    sample(a,healthy=False);advance(a,now,600,healthy=False)
    a=SecurityAlerts(a.settings,audit.append,clock=lambda:now[0],send=send)
    a.recover_uncertain();advance(a,now,90000,healthy=False)
    assert calls.count('email')==1 and calls.count('telegram:123')==1
    assert any(e['event']=='operational_notification_delivery_unknown' for e in audit)


def open_backup(a,now):
    sample(a,backup='unknown')
    with a.connect() as db:
        db.execute("UPDATE operational_state SET since=? WHERE issue='backup'",(now[0]-72*3600,))
    sample(a,backup='unknown');a.tick()


def test_backup_known_failure_retries_no_sooner_than_next_day(tmp_path):
    calls=[]
    def send(channel,text):
        calls.append(channel)
        if channel=='email':raise ConnectionRefusedError()
    a,now,_,_=harness(tmp_path,send)
    open_backup(a,now)
    advance(a,now,7200,backup='unknown')
    assert calls.count('email')==1 and calls.count('telegram:123')==1
    now[0]+=86400
    sample(a,backup='unknown');a.tick()
    assert calls.count('email')==2 and calls.count('telegram:123')==1


def test_backup_reopening_is_silent_for_seven_days_and_state_survives_upgrade(tmp_path):
    a,now,sent,audit=harness(tmp_path)
    open_backup(a,now)
    assert len(sent)==2
    advance(a,now,360)
    open_backup(a,now)
    assert len(sent)==2
    a=SecurityAlerts(a.settings,audit.append,clock=lambda:now[0],send=lambda *args:sent.append(args))
    now[0]+=86400;sample(a,backup='unknown');a.tick()
    assert len(sent)==2
    now[0]+=6*86400;sample(a,backup='unknown');a.tick()
    assert len(sent)==4
    now[0]+=8*86400;sample(a,backup='unknown');a.tick()
    assert len(sent)==4  # No recurring reminders for a continuously open incident.


def test_upgrade_existing_delivery_table_preserves_sent_state_and_quota(tmp_path):
    a,now,sent,audit=harness(tmp_path)
    open_backup(a,now)
    with a.connect() as db:
        before=[tuple(r) for r in db.execute('SELECT * FROM channels ORDER BY channel')]
        db.execute('ALTER TABLE operational_delivery DROP COLUMN last_notice_at')
        db.execute('ALTER TABLE operational_delivery DROP COLUMN last_attempt_at')
    a=SecurityAlerts(a.settings,audit.append,clock=lambda:now[0],send=lambda *args:sent.append(args))
    with a.connect() as db:
        assert [tuple(r) for r in db.execute('SELECT * FROM channels ORDER BY channel')]==before
        rows=db.execute("SELECT notified,last_notice_at FROM operational_delivery WHERE issue='backup'").fetchall()
        assert all(r['notified']==1 and r['last_notice_at']>=now[0] for r in rows)
    a.tick()
    assert len(sent)==2
