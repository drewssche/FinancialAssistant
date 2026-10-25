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


def run(settings, now=None, session_factory=SessionLocal, transport=None):
    if not settings.financial_reports_enabled:
        return {'status': 'disabled'}
    if not settings.financial_reports_start_date:
        raise ValueError('Financial reports require an explicit activation date')
    now = now or datetime.now(ZONE)
    period = latest_due(now, settings.financial_reports_start_date)
    if not period:
        return {'status': 'not_due'}
    ledger = ReportLedger(settings.financial_reports_state_dir)
    with ledger.lock() as acquired:
        if not acquired:
            return {'status': 'already_running'}
        with session_factory() as db:
            if db.get_bind().dialect.name == 'postgresql':
                db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            owner = resolve_owner(db, settings.financial_reports_telegram_id)
            job = f'{owner}-{period.due.isoformat()}'
            if all(ledger.state(job, c) == 'sent' for c in ('telegram', 'email')):
                return {'status': 'already_sent', 'job': job}
            folder = ledger.directory / job
            folder.mkdir(exist_ok=True, mode=0o700)
            snapshot = folder / 'report.json'
            if snapshot.exists():
                report = json.loads(snapshot.read_text())
            else:
                report = collect_report(db, owner, period, today=now.astimezone(ZONE).date())
                atomic_write(snapshot, json.dumps(report, default=str, ensure_ascii=False).encode())
        # Release the database connection before rendering and network calls.
        image_path, text_path = folder / 'report.png', folder / 'report.txt'
        if image_path.exists() and text_path.exists():
            png, plain = image_path.read_bytes(), text_path.read_text()
        else:
            png, plain = render_report(report)
            atomic_write(image_path, png); atomic_write(text_path, plain.encode())
        result = ledger.deliver(job, transport or ReportTransport(settings), report, png, plain)
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
