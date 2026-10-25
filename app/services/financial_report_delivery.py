"""Durable, independent channel delivery. Ambiguous sends are never replayed."""
from contextlib import contextmanager
from datetime import datetime, timezone
from email.message import EmailMessage
from hashlib import sha256
from html import escape
from pathlib import Path
import fcntl
import json
import os
import smtplib
import sqlite3
import ssl

import httpx

from app.services.financial_report_renderer import TITLES, span, money


class ReportLedger:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.directory.chmod(0o700)
        self.path = self.directory / 'deliveries.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS deliveries (job TEXT, channel TEXT, recipient_hash TEXT, state TEXT, detail TEXT, updated_at TEXT, PRIMARY KEY(job, channel))')
            db.execute('CREATE TABLE IF NOT EXISTS events (at TEXT, job TEXT, channel TEXT, state TEXT, detail TEXT)')
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def lock(self):
        with (self.directory / 'runner.lock').open('a') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
            try:
                yield True
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def state(self, job, channel):
        with self.connect() as db:
            row = db.execute('SELECT state FROM deliveries WHERE job=? AND channel=?', (job, channel)).fetchone()
        return row['state'] if row else None

    def record(self, job, channel, recipient, state, detail=''):
        # No message bodies, amounts, email addresses, tokens or raw errors in journal.
        at = datetime.now(timezone.utc).isoformat()
        digest = sha256(recipient.encode()).hexdigest()
        with self.connect() as db:
            db.execute('INSERT INTO deliveries VALUES (?,?,?,?,?,?) ON CONFLICT(job,channel) DO UPDATE SET state=excluded.state, detail=excluded.detail, updated_at=excluded.updated_at',
                       (job, channel, digest, state, detail, at))
            db.execute('INSERT INTO events VALUES (?,?,?,?,?)', (at, job, channel, state, detail))

    def recover(self):
        with self.connect() as db:
            at = datetime.now(timezone.utc).isoformat()
            rows = db.execute("SELECT job, channel FROM deliveries WHERE state='sending'").fetchall()
            for row in rows:
                db.execute("UPDATE deliveries SET state='uncertain', detail='interrupted', updated_at=? WHERE job=? AND channel=?", (at, row['job'], row['channel']))
                db.execute('INSERT INTO events VALUES (?,?,?,?,?)', (at, row['job'], row['channel'], 'uncertain', 'interrupted'))

    def deliver(self, job, transport, report, png, text, channels=None):
        result = {}
        self.recover()  # caller holds process lock
        for channel, recipient in transport.recipients.items():
            if channels is not None and channel not in channels:
                continue
            state = self.state(job, channel)
            if state in {'sent', 'uncertain'}:
                result[channel] = state
                continue
            try:
                transport.preflight(channel)
            except Exception as error:
                self.record(job, channel, recipient, 'preflight_failed', type(error).__name__)
                result[channel] = 'preflight_failed'
                continue
            # Commit before any side effect; a crash can lose a notification but
            # cannot produce a duplicate. SMTP/Bot API do not offer idempotency keys.
            self.record(job, channel, recipient, 'sending')
            try:
                receipt = transport.send(channel, report, png, text, job)
            except Exception as error:
                self.record(job, channel, recipient, 'uncertain', type(error).__name__)
                result[channel] = 'uncertain'
            else:
                self.record(job, channel, recipient, 'sent', json.dumps(receipt))
                result[channel] = 'sent'
        return result


def atomic_write(path: Path, content: bytes):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('wb') as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(content); handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)


class ReportTransport:
    def __init__(self, settings, channels=None):
        self.s = settings
        self.recipients = {'telegram': settings.financial_reports_telegram_id, 'email': settings.financial_reports_email}
        if channels is not None:
            self.recipients = {k:v for k,v in self.recipients.items() if k in channels}

    def preflight(self, channel):
        s = self.s
        if not self.recipients[channel]:
            raise ValueError('Missing report recipient')
        if channel == 'email':
            if not all((s.smtp_host, s.smtp_from, s.smtp_username, s.smtp_password)):
                raise ValueError('Email transport is not configured')
            if '@' not in self.recipients[channel] or any(x in self.recipients[channel] for x in '\r\n,;'):
                raise ValueError('One email recipient required')
            return
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            response = client.post(f'https://api.telegram.org/bot{s.telegram_bot_token}/getChat', data={'chat_id': self.recipients[channel]})
            response.raise_for_status(); body = response.json()
            chat = body.get('result') or {}
            if not body.get('ok') or chat.get('type') != 'private' or str(chat.get('id')) != self.recipients[channel]:
                raise ValueError('Personal Telegram chat required')

    def send(self, channel, report, png, text, job):
        s = self.s
        title = f"ФинАсист · {TITLES[report['kind']]}"
        period = span(report['start'], report['end'])
        cur = report['current']; currency = report['currency']
        caption = (f"{title}\n{period}\n\nПришло {money(cur['cashflow_income_total'])} {currency}\n"
                   f"Ушло {money(cur['cashflow_expense_total'])} {currency}\nРазница {money(cur['cashflow_total'], True)} {currency}\n\n"
                   'Категории, крупные траты и ближайшие планы — на инфографике.')
        if channel == 'telegram':
            with httpx.Client(timeout=45, follow_redirects=False) as client:
                response = client.post(f'https://api.telegram.org/bot{s.telegram_bot_token}/sendPhoto',
                    data={'chat_id': self.recipients[channel], 'caption': caption},
                    files={'photo': ('financial-report.png', png, 'image/png')})
                response.raise_for_status(); body = response.json()
                result = body.get('result') or {}
                if not body.get('ok') or not result.get('photo'):
                    raise RuntimeError('Photo delivery not acknowledged')
                return {'message_id': result['message_id']}
        message = EmailMessage()
        message['Subject'] = f'{title} · {period}'
        message['From'], message['To'] = s.smtp_from, self.recipients[channel]
        identity = sha256(job.encode()).hexdigest()[:32]
        message['Message-ID'] = f'<financial-report-{identity}@financialassistant.local>'
        message.set_content(text)
        message.add_alternative(f'''<html><body style="margin:0;background:#080e18;color:#f1f5fc;font-family:Arial,sans-serif">
<div style="max-width:720px;margin:auto;padding:16px"><h2>{escape(title)}</h2><p>{escape(period)}</p>
<img src="cid:financial-report" width="720" style="display:block;width:100%;height:auto" alt="{escape(caption, quote=True)}">
<details><summary>Текст отчёта</summary><pre style="white-space:pre-wrap;font:15px Arial">{escape(text)}</pre></details>
</div></body></html>''', subtype='html')
        message.get_payload()[-1].add_related(png, maintype='image', subtype='png', cid='<financial-report>', filename='financial-report.png', disposition='inline')
        context = ssl.create_default_context()
        if s.smtp_security == 'ssl':
            client = smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, timeout=30, context=context)
        else:
            client = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30)
        with client:
            if s.smtp_security == 'starttls':
                client.ehlo(); client.starttls(context=context); client.ehlo()
            client.login(s.smtp_username, s.smtp_password)
            if client.send_message(message):
                raise RuntimeError('Email recipient refused')
        return {'smtp_accepted': True}
