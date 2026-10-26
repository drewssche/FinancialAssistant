"""Server-side per-profile reporting; delivery jobs retain their original IDs."""
from datetime import datetime
import json

from sqlalchemy import select, text
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.db.models import User, UserPreference
from app.db.models.auth_identity import AuthIdentity
from app.services.financial_report_data import ZONE, latest_due, collect_report
from app.services.financial_report_delivery import ReportLedger, ReportTransport, atomic_write
from app.services.financial_report_renderer import render_report
from app.services.financial_report_preferences import (
    read_report_preferences, configured_for, legacy_owner, activation_date, report_recipients,
)


def run_user(settings, now, session_factory, ledger, owner, transport=None, transport_factory=None):
    with session_factory() as db:
        if db.get_bind().dialect.name == 'postgresql':
            db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        if not configured_for(db,owner,settings):return {'status':'unavailable'}
        prefs=read_report_preferences(db,owner,settings)
        if not prefs.enabled:return {'status':'paused'}
        start=activation_date(db,owner,settings)
        if not start:return {'status':'not_activated'}
        period=latest_due(now,start,kinds=prefs.kinds,send_time=prefs.send_time)
        if not period:return {'status':'not_due'}
        job=f'{owner}-{period.due.isoformat()}'
        if all(ledger.state(job,c)=='sent' for c in prefs.channels):
            return {'status':'already_sent','job':job}
        folder=ledger.directory/job
        folder.mkdir(exist_ok=True,mode=0o700)
        snapshot=folder/'report.json'
        if snapshot.exists():
            report=json.loads(snapshot.read_text())
            if report['kind']!=period.kind and not any(ledger.state(job,c) in {'sent','sending','uncertain'} for c in ('telegram','email')):
                report=collect_report(db,owner,period,today=now.astimezone(ZONE).date(),kinds=prefs.kinds)
                atomic_write(snapshot,json.dumps(report,default=str,ensure_ascii=False).encode())
                for artifact in ('report.png','report.txt'):(folder/artifact).unlink(missing_ok=True)
        else:
            report=collect_report(db,owner,period,today=now.astimezone(ZONE).date(),kinds=prefs.kinds)
            atomic_write(snapshot,json.dumps(report,default=str,ensure_ascii=False).encode())
    image_path,text_path=folder/'report.png',folder/'report.txt'
    if image_path.exists() and text_path.exists():
        png,plain=image_path.read_bytes(),text_path.read_text()
    else:
        png,plain=render_report(report)
        atomic_write(image_path,png);atomic_write(text_path,plain.encode())
    # Recheck approval, channel switches and confirmed recipient after rendering.
    with session_factory() as db:
        if not configured_for(db,owner,settings):return {'status':'settings_changed','job':job}
        prefs=read_report_preferences(db,owner,settings)
        recipients=report_recipients(db,owner,settings)
        start=activation_date(db,owner,settings)
    still_due=latest_due(now,start,kinds=prefs.kinds,send_time=prefs.send_time) if start else None
    if not prefs.enabled or report['kind'] not in prefs.kinds or not still_due or still_due.due!=period.due:
        return {'status':'settings_changed','job':job}
    channels=[c for c in prefs.channels if c in recipients]
    sender=transport or (transport_factory(settings,channels,recipients=recipients) if transport_factory else ReportTransport(settings,channels,recipients=recipients))
    result=ledger.deliver(job,sender,report,png,plain,channels=channels)
    for channel in prefs.channels:
        if channel not in recipients:result[channel]='recipient_unavailable'
    return {'status':'processed','job':job,'channels':result}


def run(settings,now=None,session_factory=SessionLocal,transport=None,transport_factory=None):
    if not settings.financial_reports_enabled:return {'status':'disabled'}
    if not settings.financial_reports_start_date:
        raise ValueError('Financial reports require an explicit activation date')
    now=now or datetime.now(ZONE)
    ledger=ReportLedger(settings.financial_reports_state_dir)
    with ledger.lock() as acquired:
        if not acquired:return {'status':'already_running'}
        with session_factory() as db:
            ids=db.scalars(select(User.id).join(AuthIdentity,AuthIdentity.user_id==User.id)
                           .where(User.status.in_(['approved','active']),AuthIdentity.provider=='telegram').distinct().order_by(User.id)).all()
            owners=[]
            for uid in ids:
                row=db.get(UserPreference,uid)
                if legacy_owner(db,uid,settings) or (row and 'financial_reports' in (row.data or {})):
                    owners.append(uid)
        results=[]
        for owner in owners:
            try:
                result=run_user(settings,now,session_factory,ledger,owner,transport,transport_factory)
            except Exception as error:
                # A failure in one profile must not block others or expose payloads.
                result={'status':'failed','error_type':type(error).__name__}
            results.append({'user_id':owner,**result})
        if len(results)==1:
            return {k:v for k,v in results[0].items() if k!='user_id'}
        return {'status':'processed' if results else 'no_subscribers','users':results}


def main():
    try:result=run(get_settings())
    except Exception as error:
        print(json.dumps({'status':'failed','error_type':type(error).__name__}));return 1
    print(json.dumps(result))
    rows=result.get('users',[result])
    return int(any(r.get('status')=='failed' or any(state!='sent' for state in r.get('channels',{}).values()) for r in rows))


if __name__ == '__main__':
    raise SystemExit(main())
