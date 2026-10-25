"""Critical incident alerts; routine observations remain in the journal only."""
from datetime import datetime, timezone
from contextlib import contextmanager
from email.message import EmailMessage
from email.utils import make_msgid
from html import escape
import json
import logging
from pathlib import Path
import smtplib
import sqlite3
import ssl
from threading import Event, Thread
from time import time
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx

from app.core.config import get_settings
from app.services import operations_alert_service as operations

LOG = logging.getLogger(__name__)
BATCH_SECONDS = 60
COOLDOWN_SECONDS = 3600
DAILY_LIMIT = 2
INCIDENT_QUIET_SECONDS = 6 * 3600
POLICY_VERSION = 2


def qualifies(event):
    return event.get('event') == 'security_notification_test' or (
        event.get('event') in {'repeated_access_failure', 'rate_would_limit'}
        and event.get('method') == 'POST'
        and event.get('path') in {'/api/v1/auth/telegram', '/api/v1/auth/telegram/browser'}
        and event.get('status') in {400, 401, 403, 422}
        and event.get('login_failures_in_window', 0) >= 50)


def merge(left, right):
    result = dict(left or {})
    result['first'] = min(result.get('first', right['first']), right['first'])
    result['last'] = max(result.get('last', 0), right['last'])
    result['samples'] = result.get('samples', 0) + right.get('samples', 0)
    for key in ('sources', 'paths', 'kinds', 'users', 'changes'):
        result[key] = sorted(set(result.get(key, [])) | set(right.get(key, [])))[:10]
    result['retries'] = max(result.get('retries', 0), right.get('retries', 0))
    result['policy'] = right.get('policy')
    snapshots = [p['login_snapshot'] for p in (left or {}, right) if p.get('login_snapshot')]
    if snapshots:
        result['login_snapshot'] = max(snapshots, key=lambda p: (p['count'], p['at']))
    return result


def summarize(event, now):
    payload = {'policy': POLICY_VERSION, 'first': now, 'last': now, 'samples': 1,
        'sources': [str(event['client_ip'])[:64]] if event.get('client_ip') else [],
        'paths': [str(event['path'])[:160]] if event.get('path') else [],
        'kinds': [str(event.get('event', 'security_event'))[:64]],
        'users': [str(event['user_id'])[:20]] if isinstance(event.get('user_id'), int) else [],
        'changes': [f"User {event['target_user_id']}: {event['previous_status']} -> {event['next_status']}"] if event.get('event') == 'access_status_changed' else [],
        'retries': 0}
    if type(event.get('login_failures_in_window')) is int and event['login_failures_in_window'] >= 50:
        buckets = event.get('login_failure_buckets')
        valid = (isinstance(buckets, list) and 1 <= len(buckets) <= 5
                 and all(type(v) is int and v >= 0 for v in buckets)
                 and sum(buckets) == event['login_failures_in_window'])
        payload['login_snapshot'] = {'count': event['login_failures_in_window'], 'at': now,
            'source': str(event.get('client_ip', '—'))[:64],
            'buckets': buckets if valid else [], 'window_started_at': event.get('login_window_started_at')}
    return payload


def build_text(payload):
    zone = ZoneInfo('Europe/Minsk')
    start = datetime.fromtimestamp(payload['first'], zone).strftime('%d.%m %H:%M')
    end = datetime.fromtimestamp(payload['last'], zone).strftime('%d.%m %H:%M')
    heading = 'ФинАсист — проверка доставки уведомлений' if payload['kinds'] == ['security_notification_test'] else 'ФинАсист — массовые попытки входа'
    basis = ('Ручная проверка канала доставки.' if payload['kinds'] == ['security_notification_test']
             else 'Основание: не менее 50 отказов входа за 5 минут с одного адреса.')
    snapshot = payload.get('login_snapshot')
    observed = (f'Максимальный срез: {snapshot["count"]} отказов входа с {snapshot["source"]} '
                f'в окне до 5 минут; {datetime.fromtimestamp(snapshot["at"], zone).strftime("%d.%m %H:%M")} (Минск).\n'
                if snapshot and payload['kinds'] != ['security_notification_test'] else '')
    return (heading + '\n'
        f'Период: {start} — {end} (Минск)\n'
        f'Записей наблюдения: {payload["samples"]} (повторы могут быть объединены)\n'
        f'{observed}'
        f'События: {", ".join(payload["kinds"])}\n'
        f'Источники: {", ".join(payload["sources"]) or "—"}\n'
        f'Маршруты: {", ".join(payload["paths"]) or "—"}\n'
        f'Проверенные User ID: {", ".join(payload["users"]) or "—"}\n\n'
        f'Изменения доступа: {"; ".join(payload.get("changes", [])) or "—"}\n'
        f'{basis}\n'
        'Это не подтверждение успешного взлома. Автоблокировки выключены. Повторы инцидента остаются в журнале.\n'
        'Подробности: серверный журнал security.jsonl.')


class SecurityAlerts:
    def __init__(self, settings, journal, *, clock=time, send=None):
        self.settings, self.journal, self.clock = settings, journal, clock
        self.send = send
        self.path = Path(settings.security_event_log_path).with_name('security-alerts.sqlite3')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.stop_event = Event()
        self.thread = None
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('''CREATE TABLE IF NOT EXISTS channels (
                channel TEXT PRIMARY KEY, pending TEXT, inflight TEXT,
                next_at REAL NOT NULL DEFAULT 0, day TEXT NOT NULL DEFAULT '',
                attempts INTEGER NOT NULL DEFAULT 0)''')
            db.execute('CREATE TABLE IF NOT EXISTS access_events (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS alert_policy (version INTEGER PRIMARY KEY)')
            db.execute('CREATE TABLE IF NOT EXISTS security_incidents (channel TEXT PRIMARY KEY, last_seen REAL NOT NULL)')
            operations.initialize(db)
            for channel in self.channels:
                db.execute('INSERT OR IGNORE INTO channels(channel) VALUES (?)', (channel,))
            if not db.execute('SELECT 1 FROM alert_policy WHERE version=?', (POLICY_VERSION,)).fetchone():
                # Old informational summaries must not arrive after the policy change.
                # Keep the journal and uncertain in-flight deliveries for recovery.
                db.execute("UPDATE channels SET pending=NULL,next_at=0,day='',attempts=0")
                db.execute("DELETE FROM operational_delivery WHERE issue='backup'")
                db.execute("DELETE FROM operational_state WHERE issue='backup'")
                db.execute('INSERT INTO alert_policy VALUES (?)', (POLICY_VERSION,))
        self.path.chmod(0o600)

    @property
    def channels(self):
        return ['telegram:' + value for value in sorted(self.settings.admin_telegram_id_set)] + (
            ['email'] if self.settings.security_alert_email else [])

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=1)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def audit(self, event, channel, **details):
        self.journal({'timestamp': datetime.now(timezone.utc).isoformat(),
            'event': event, 'channel': channel, **details})

    def record(self, event):
        critical = qualifies(event)
        if not critical and event.get('event') != 'access_status_changed':
            return
        payload = summarize(event, self.clock())
        try:
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if event.get('event') == 'access_status_changed':
                    db.execute('INSERT INTO access_events(payload) VALUES (?)', (json.dumps(event),))
                    db.execute('DELETE FROM access_events WHERE id NOT IN (SELECT id FROM access_events ORDER BY id DESC LIMIT 100)')
                if not critical:
                    return
                for channel in self.channels:
                    row = db.execute('SELECT pending FROM channels WHERE channel=?', (channel,)).fetchone()
                    pending = json.loads(row['pending']) if row['pending'] else {}
                    if pending.get('policy') != POLICY_VERSION:
                        pending = {}
                    if event.get('event') != 'security_notification_test':
                        previous = db.execute('SELECT last_seen FROM security_incidents WHERE channel=?', (channel,)).fetchone()
                        db.execute('INSERT OR REPLACE INTO security_incidents VALUES (?,?)', (channel, self.clock()))
                        if previous and self.clock() - previous['last_seen'] < INCIDENT_QUIET_SECONDS and not pending:
                            continue
                    combined = merge(pending, payload)
                    db.execute('UPDATE channels SET pending=? WHERE channel=?', (json.dumps(combined), channel))
        except (OSError, sqlite3.Error):
            LOG.error('security_alert_queue_write_failed')

    def available(self, channel):
        s = self.settings
        if channel.startswith('telegram:'):
            return bool(s.telegram_bot_token and s.telegram_bot_token != 'change_me')
        return bool(s.smtp_host and s.smtp_from and s.smtp_username and s.smtp_password)

    def recover_uncertain(self):
        # A crash after remote acceptance has an unknown delivery outcome. Do not
        # replay it automatically and risk duplicate alerts after every restart.
        with self.connect() as db:
            rows = db.execute('SELECT channel,inflight FROM channels WHERE inflight IS NOT NULL').fetchall()
            for row in rows:
                payload = json.loads(row['inflight'])
                self.audit('security_notification_unknown_after_restart', row['channel'], notification_id=payload['id'])
                if payload.get('operations'):
                    operations.acknowledge(db, row['channel'], payload['operations'])
                db.execute('UPDATE channels SET inflight=NULL WHERE channel=?', (row['channel'],))

    def tick(self, *, force_batch=False):
        now = self.clock()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for row in db.execute('SELECT id,payload FROM access_events ORDER BY id').fetchall():
                self.journal(json.loads(row['payload']))
                db.execute('DELETE FROM access_events WHERE id=?', (row['id'],))
        day = datetime.fromtimestamp(now, ZoneInfo('Europe/Minsk')).date().isoformat()
        for channel in self.channels:
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT * FROM channels WHERE channel=?', (channel,)).fetchone()
                if not row['pending'] or row['inflight']:
                    continue
                payload = json.loads(row['pending'])
                if payload.get('policy') != POLICY_VERSION:
                    db.execute('UPDATE channels SET pending=NULL WHERE channel=?', (channel,))
                    continue
                if not payload.get('retries') and payload['kinds'] != ['security_notification_test'] and now - payload['last'] >= INCIDENT_QUIET_SECONDS:
                    self.audit('security_notification_expired', channel)
                    db.execute('UPDATE channels SET pending=NULL WHERE channel=?', (channel,))
                    continue
                if now < row['next_at']:
                    continue
                if not force_batch and now < payload['first'] + BATCH_SECONDS:
                    continue
                attempts = row['attempts'] if row['day'] == day else 0
                if attempts >= DAILY_LIMIT:
                    continue
                if not self.available(channel):
                    self.audit('security_notification_unconfigured', channel)
                    db.execute('UPDATE channels SET next_at=? WHERE channel=?', (now + 86400, channel))
                    continue
                payload['id'] = str(uuid4())
                db.execute('UPDATE channels SET pending=NULL,inflight=?,next_at=?,day=?,attempts=? WHERE channel=?',
                    (json.dumps(payload), now + COOLDOWN_SECONDS, day, attempts + 1, channel))
            self.audit('security_notification_attempted', channel, notification_id=payload['id'])
            try:
                self.send_notification(channel, build_text(payload), payload)
            except Exception as exc:
                # Never log exception text: HTTP errors may contain bot tokens,
                # SMTP responses may contain addresses or authentication data.
                self.audit('security_notification_failed', channel, notification_id=payload['id'], error=type(exc).__name__)
                payload['retries'] += 1
                with self.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    row = db.execute('SELECT pending FROM channels WHERE channel=?', (channel,)).fetchone()
                    pending = json.loads(row['pending']) if row['pending'] else {}
                    if payload['retries'] < 3:
                        pending = merge(pending, payload)
                    else:
                        self.audit('security_notification_abandoned', channel, notification_id=payload['id'])
                    db.execute('UPDATE channels SET inflight=NULL,pending=? WHERE channel=?',
                        (json.dumps(pending) if pending else None, channel))
            else:
                self.audit('security_notification_sent', channel, notification_id=payload['id'])
                with self.connect() as db:
                    db.execute('UPDATE channels SET inflight=NULL WHERE channel=?', (channel,))

        operations.tick(self, cooldown=COOLDOWN_SECONDS, daily_limit=DAILY_LIMIT)

    def send_notification(self, channel, text, payload):
        if self.send is not None:
            return self.send(channel, text)
        return self.deliver(channel, text, payload=payload)

    def deliver(self, channel, text, *, payload=None):
        s = self.settings
        png = None
        caption = text
        if payload is not None:
            try:
                from app.services.incident_infographic import render_notification
                png, caption = render_notification(payload)
            except Exception as exc:
                # Fallback is only safe BEFORE contacting either delivery service.
                self.audit('notification_image_failed', channel, error=type(exc).__name__)
        if channel.startswith('telegram:'):
            with httpx.Client(timeout=8, follow_redirects=False) as client:
                if png:
                    response = client.post(f'https://api.telegram.org/bot{s.telegram_bot_token}/sendPhoto',
                        data={'chat_id': channel.split(':', 1)[1], 'caption': caption[:1000]},
                        files={'photo': ('finassist-incident.png', png, 'image/png')})
                else:
                    response = client.post(f'https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage', json={
                        'chat_id': channel.split(':', 1)[1], 'text': text[:3900], 'disable_web_page_preview': True})
                response.raise_for_status()
                body = response.json()
                if body.get('ok') is not True or (png and not body.get('result', {}).get('photo')):
                    raise RuntimeError('Telegram delivery not acknowledged')
            self.audit('notification_media_accepted', channel, media='photo' if png else 'text')
            return
        message = EmailMessage()
        message['Subject'] = text.splitlines()[0].replace(' — ', ': ', 1)
        message['From'], message['To'] = s.smtp_from, s.security_alert_email
        message['Message-ID'] = make_msgid()
        message.set_content(text)
        if png:
            cid = make_msgid()
            message.add_alternative(
                '<!doctype html><html lang="ru"><body style="margin:0;padding:20px;background:#080e18;color:#f1f5fc;font-family:Arial,sans-serif">'
                '<div style="max-width:600px;margin:auto">'
                f'<img src="cid:{cid[1:-1]}" width="600" style="width:100%;height:auto;display:block" alt="{escape(caption, quote=True)}">'
                f'<p style="white-space:pre-wrap;font-size:15px;line-height:1.5;color:#a5b7ce">{escape(text)}</p>'
                '</div></body></html>', subtype='html')
            message.get_payload()[-1].add_related(png, maintype='image', subtype='png', cid=cid, disposition='inline')
        context = ssl.create_default_context()
        if s.smtp_security == 'ssl':
            client = smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, timeout=8, context=context)
        else:
            client = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=8)
        with client:
            if s.smtp_security == 'starttls':
                client.ehlo()
                client.starttls(context=context)
                client.ehlo()
            client.login(s.smtp_username, s.smtp_password)
            if client.send_message(message):
                raise RuntimeError('SMTP recipient rejected')
        self.audit('notification_media_accepted', channel, media='inline_png' if png else 'text')

    def run(self):
        try:
            self.recover_uncertain()
        except (OSError, sqlite3.Error):
            LOG.error('security_alert_recovery_failed')
        while not self.stop_event.wait(30):
            try:
                self.tick()
            except Exception:
                LOG.error('security_alert_worker_failed')

    def start(self):
        self.thread = Thread(target=self.run, name='security-alerts', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=10)


def record_access_change(*, admin_id, target_user_id, previous_status, next_status):
    settings = get_settings()
    if not settings.security_alerts_enabled or not settings.security_event_log_path:
        return
    try:
        SecurityAlerts(settings, lambda event: None).record({
            'timestamp': datetime.now(timezone.utc).isoformat(), 'event': 'access_status_changed',
            'user_id': admin_id, 'target_user_id': target_user_id,
            'previous_status': previous_status, 'next_status': next_status,
            'path': '/api/v1/admin/users/{user_id}',
        })
    except (OSError, sqlite3.Error):
        LOG.error('security_access_audit_queue_failed')
