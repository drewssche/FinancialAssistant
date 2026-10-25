"""Single server-side reporting entry point; never logs credentials or financial data."""
from datetime import datetime
import json
from pathlib import Path

from sqlalchemy import text
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.financial_report_data import ZONE, latest_due, collect_report, resolve_owner
from app.services.financial_report_delivery import ReportLedger, ReportTransport, atomic_write
from app.services.financial_report_renderer import render_report
from app.services.financial_report_preferences import read_report_preferences


def run(settings, now=None, session_factory=SessionLocal, transport=None):
    if not settings.financial_reports_enabled:
        return {'status': 'disabled'}
    if not settings.financial_reports_start_date:
        raise ValueError('Financial reports require an explicit activation date')
    now = now or datetime.now(ZONE)
    ledger = ReportLedger(settings.financial_reports_state_dir)
    with ledger.lock() as acquired:
        if not acquired:
            return {'status': 'already_running'}
        with session_factory() as db:
            if db.get_bind().dialect.name == 'postgresql':
                db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            owner = resolve_owner(db, settings.financial_reports_telegram_id)
            prefs = read_report_preferences(db, owner)
            if not prefs.enabled:
                return {'status': 'paused'}
            period = latest_due(now, settings.financial_reports_start_date, kinds=prefs.kinds, send_time=prefs.send_time)
            if not period:
                return {'status': 'not_due'}
            job = f'{owner}-{period.due.isoformat()}'
            if all(ledger.state(job, c) == 'sent' for c in prefs.channels):
                return {'status': 'already_sent', 'job': job}
            folder = ledger.directory / job
            folder.mkdir(exist_ok=True, mode=0o700)
            snapshot = folder / 'report.json'
            if snapshot.exists():
                report = json.loads(snapshot.read_text())
                if report['kind'] != period.kind and not any(ledger.state(job,c) in {'sent','sending','uncertain'} for c in ('telegram','email')):
                    report = collect_report(db, owner, period, today=now.astimezone(ZONE).date(), kinds=prefs.kinds)
                    atomic_write(snapshot, json.dumps(report, default=str, ensure_ascii=False).encode())
                    for artifact in ('report.png','report.txt'):
                        (folder / artifact).unlink(missing_ok=True)
            else:
                report = collect_report(db, owner, period, today=now.astimezone(ZONE).date(), kinds=prefs.kinds)
                atomic_write(snapshot, json.dumps(report, default=str, ensure_ascii=False).encode())
        # Release the database connection before rendering and network calls.
        image_path, text_path = folder / 'report.png', folder / 'report.txt'
        if image_path.exists() and text_path.exists():
            png, plain = image_path.read_bytes(), text_path.read_text()
        else:
            png, plain = render_report(report)
            atomic_write(image_path, png); atomic_write(text_path, plain.encode())
        # Honour a pause or channel change made while the image was being built.
        with session_factory() as db:
            resolve_owner(db, settings.financial_reports_telegram_id)
            prefs = read_report_preferences(db, owner)
        still_due = latest_due(now, settings.financial_reports_start_date, kinds=prefs.kinds, send_time=prefs.send_time)
        if not prefs.enabled or report['kind'] not in prefs.kinds or not still_due or still_due.due != period.due:
            return {'status': 'settings_changed', 'job': job}
        result = ledger.deliver(job, transport or ReportTransport(settings, prefs.channels), report, png, plain, channels=prefs.channels)
        return {'status': 'processed', 'job': job, 'channels': result}


def main():
    try:
        result = run(get_settings())
    except Exception as error:
        # HTTP exceptions contain bot-token URLs; never print raw exception text.
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}))
        return 1
    print(json.dumps(result))
    return int(any(state != 'sent' for state in result.get('channels', {}).values()))


if __name__ == '__main__':
    raise SystemExit(main())
