"""Persistent incident transitions. Shares security delivery quotas and transports."""
from datetime import datetime
import json
from zoneinfo import ZoneInfo

LABELS = {
    'backup': ('Резервная копия', 'Выгрузка резервных копий снова подтверждена.'),
    'bot': ('Telegram-бот', 'Бот снова стабильно работает.'),
}
REASONS = {
    'backup_unknown': 'Не менее 72 часов нет подтверждения свежей автоматической копии вне сервера.',
    'backup_stale': 'Не менее 36 часов подтверждается устаревшая внешняя копия (старше 36 часов).',
    'backup_failed': 'Последняя попытка резервного копирования завершилась с ошибкой.',
    'backup_retention': 'Не удалось выполнить очистку старых внешних копий.',
    'bot_unhealthy': 'Бот не работает или его healthcheck не подтверждает работоспособность.',
    'bot_restarts': 'Не менее трёх перезапусков бота за 30 минут.',
}


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS operational_state (
        issue TEXT PRIMARY KEY, active INTEGER NOT NULL DEFAULT 0,
        candidate INTEGER NOT NULL, since REAL NOT NULL, last_seen REAL NOT NULL,
        reason TEXT NOT NULL, changed REAL NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS operational_delivery (
        channel TEXT NOT NULL, issue TEXT NOT NULL, notified INTEGER NOT NULL DEFAULT 0,
        target INTEGER NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(channel,issue))''')
    db.execute('CREATE TABLE IF NOT EXISTS operational_probe (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')


def observe(alerts, sample):
    now = alerts.clock()
    if set(sample) != {'backup', 'bot'} or sample['backup'] not in {'ok', 'unknown', 'stale', 'failed', 'retention'}:
        raise ValueError('Invalid operational sample')
    bot = sample['bot']
    if (not isinstance(bot, dict) or set(bot) != {'id', 'restarts', 'healthy'}
        or not isinstance(bot['id'], str) or len(bot['id']) > 64
        or type(bot['restarts']) is not int or bot['restarts'] < 0
        or type(bot['healthy']) is not bool):
        raise ValueError('Invalid bot sample')
    with alerts.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT payload FROM operational_probe WHERE id=1').fetchone()
        prev = json.loads(row[0]) if row else {}
        # Never treat the pre-installation lifetime counter as a current burst.
        events = [t for t in prev.get('events', []) if now - 1800 <= t <= now]
        if prev.get('id') == bot['id']:
            events += [now] * min(3, max(0, bot['restarts'] - prev.get('restarts', 0)))
        elif prev.get('id') and bot['id']:
            events.append(now)
        db.execute('INSERT OR REPLACE INTO operational_probe VALUES (1,?)',
            (json.dumps({**bot, 'events': events[-3:]}),))
        # A failed retry/retention job with a recent offsite copy is journal-only.
        reasons = {'backup': 'backup_' + sample['backup'] if sample['backup'] in {'unknown', 'stale'} else '',
            'bot': 'bot_unhealthy' if not bot['healthy'] else ('bot_restarts' if len(events) >= 3 else '')}
        for issue, reason in reasons.items():
            bad = int(bool(reason))
            row = db.execute('SELECT * FROM operational_state WHERE issue=?', (issue,)).fetchone()
            active = row['active'] if row else 0
            # A gap in sampling does not prove continuous failure or recovery.
            since = row['since'] if row and row['candidate'] == bad and 0 <= now - row['last_seen'] <= 180 else now
            delay = ((36 * 3600 if reason == 'backup_stale' else 72 * 3600)
                     if issue == 'backup' else 600) if bad else 300
            changed = row['changed'] if row else now
            if bad != active and now - since >= delay:
                active, changed = bad, now
                alerts.audit('operational_incident_opened' if bad else 'operational_incident_recovered', 'monitor', issue=issue, reason=reason)
            db.execute('INSERT OR REPLACE INTO operational_state VALUES (?,?,?,?,?,?,?)',
                (issue, active, bad, since, now, reason, changed))
            for channel in alerts.channels:
                db.execute('INSERT OR IGNORE INTO operational_delivery(channel,issue) VALUES (?,?)', (channel, issue))
                db.execute('UPDATE operational_delivery SET target=?, attempts=0 WHERE channel=? AND issue=? AND target<>?',
                    (active, channel, issue, active))


def pending(db, channel, now):
    # Recovery is recorded, but never creates another email/Telegram message.
    db.execute('''UPDATE operational_delivery SET notified=0 WHERE channel=?
        AND issue IN (SELECT issue FROM operational_state WHERE active=0)''', (channel,))
    return [dict(row) for row in db.execute('''SELECT s.issue,s.active,s.reason,s.changed FROM operational_state s
        JOIN operational_delivery d ON d.issue=s.issue WHERE d.channel=?
        AND s.active=1 AND d.notified<>s.active AND d.attempts<3 AND s.last_seen>=?
        AND s.candidate=s.active ORDER BY s.issue''', (channel, now - 180))]


def acknowledge(db, channel, operations):
    for item in operations:
        db.execute('UPDATE operational_delivery SET notified=? WHERE channel=? AND issue=?',
            (item['active'], channel, item['issue']))


def build_text(operations):
    lines = ['ФинАсист — состояние сервисов']
    for item in operations:
        label, recovery = LABELS[item['issue']]
        message = REASONS[item['reason']] if item['active'] else recovery
        stamp = datetime.fromtimestamp(item['changed'], ZoneInfo('Europe/Minsk')).strftime('%d.%m %H:%M')
        lines.append(f'{label} · {stamp} (Минск): {message}')
    lines.append('Повторы этого состояния не отправляются. Подробности записаны в серверный журнал.')
    return '\n\n'.join(lines)


def tick(alerts, *, cooldown, daily_limit):
    now = alerts.clock()
    day = datetime.fromtimestamp(now, ZoneInfo('Europe/Minsk')).date().isoformat()
    for channel in alerts.channels:
        with alerts.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM channels WHERE channel=?', (channel,)).fetchone()
            operations = pending(db, channel, now)
            count = row['attempts'] if row['day'] == day else 0
            if not operations or row['inflight'] or now < row['next_at'] or count >= daily_limit:
                continue
            if not alerts.available(channel):
                alerts.audit('operational_notification_unconfigured', channel)
                db.execute('UPDATE channels SET next_at=? WHERE channel=?', (now + 86400, channel))
                continue
            from uuid import uuid4
            payload = {'id': str(uuid4()), 'operations': operations}
            db.execute('UPDATE channels SET inflight=?,next_at=?,day=?,attempts=? WHERE channel=?',
                (json.dumps(payload), now + cooldown, day, count + 1, channel))
            for item in operations:
                db.execute('UPDATE operational_delivery SET attempts=attempts+1 WHERE channel=? AND issue=?', (channel, item['issue']))
        alerts.audit('operational_notification_attempted', channel, notification_id=payload['id'])
        try:
            alerts.send(channel, build_text(operations))
        except Exception as exc:
            alerts.audit('operational_notification_failed', channel, notification_id=payload['id'], error=type(exc).__name__)
        else:
            with alerts.connect() as db:
                acknowledge(db, channel, operations)
            alerts.audit('operational_notification_sent', channel, notification_id=payload['id'])
        finally:
            with alerts.connect() as db:
                db.execute('UPDATE channels SET inflight=NULL WHERE channel=?', (channel,))
