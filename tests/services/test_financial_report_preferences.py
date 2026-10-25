from datetime import date,datetime
from types import SimpleNamespace
from pydantic import ValidationError
import pytest
from sqlalchemy.orm import sessionmaker

from tests.services.test_financial_reports import db,Transport
from app.services.financial_report_preferences import ReportPreferences,save_report_preferences,read_report_preferences,view_report_preferences
from app.services.financial_report_data import scheduled_period,latest_due,ZONE
from app.services.preferences_service import PreferencesService
from app.services.financial_report_delivery import ReportLedger
from scripts.run_financial_reports import run


def settings(tmp_path):
    return SimpleNamespace(financial_reports_enabled=True,financial_reports_telegram_id='123',financial_reports_email='owner@example.test',financial_reports_start_date=date(2020,10,26),financial_reports_state_dir=str(tmp_path))


def test_owner_api_validates_isolation_and_survives_old_general_payload(db,tmp_path,monkeypatch):
    import app.api.v1.preferences as routes
    monkeypatch.setattr(routes,'get_settings',lambda:settings(tmp_path))
    from app.api.v1.preferences import get_financial_report_preferences,update_financial_report_preferences
    assert get_financial_report_preferences(1,db)['available'] is True
    assert get_financial_report_preferences(2,db)['email_address'] is None
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:update_financial_report_preferences(ReportPreferences(),2,db)
    assert e.value.status_code==403
    saved=update_financial_report_preferences(ReportPreferences(enabled=False,telegram=False),1,db)
    assert saved['next_send'] is None
    merged=PreferencesService._preserve_currency_runtime_state({'financial_reports':saved['settings']},{'financial_reports':{'enabled':True},'ui':{'scale_percent':100}})
    assert merged['financial_reports']['enabled'] is False
    assert PreferencesService._preserve_currency_runtime_state({}, {'financial_reports':{'enabled':True}}).get('financial_reports') is None


@pytest.mark.parametrize('data',[{'send_time':'09:07'},{'send_time':'24:00'},{'email_address':'attacker@example.test'},{'weekly':False,'monthly':False,'yearly':False},{'telegram':False,'email':False},{'enabled':'false'}])
def test_invalid_controls_rejected(data):
    with pytest.raises(ValidationError):ReportPreferences(**data)


def test_schedule_uses_selected_periods_and_exact_time():
    assert scheduled_period(date(2029,1,1),{'week','month'}).kind=='month'
    assert scheduled_period(date(2029,1,1),{'week'}).kind=='week'
    assert scheduled_period(date(2029,1,1),set()) is None
    assert latest_due(datetime(2020,10,26,10,14,tzinfo=ZONE),date(2020,10,26),send_time='10:15') is None
    assert latest_due(datetime(2020,10,26,10,15,tzinfo=ZONE),date(2020,10,26),send_time='10:15').kind=='week'


def test_saved_pause_channels_time_and_resume_affect_actual_runner(db,tmp_path):
    s=settings(tmp_path);factory=sessionmaker(bind=db.get_bind());t=Transport()
    save_report_preferences(db,1,ReportPreferences(enabled=False))
    assert run(s,datetime(2020,10,26,11,tzinfo=ZONE),factory,t)['status']=='paused'
    save_report_preferences(db,1,ReportPreferences(email=False,send_time='10:15'))
    assert run(s,datetime(2020,10,26,10,14,tzinfo=ZONE),factory,t)['status']=='not_due'
    assert run(s,datetime(2020,10,26,10,15,tzinfo=ZONE),factory,t)['channels']=={'telegram':'sent'}
    assert t.calls==['telegram']
    save_report_preferences(db,1,ReportPreferences())
    run(s,datetime(2020,10,26,10,30,tzinfo=ZONE),factory,t)
    assert t.calls==['telegram','email']
    save_report_preferences(db,1,ReportPreferences(enabled=False))
    save_report_preferences(db,1,ReportPreferences())
    assert run(s,datetime(2020,10,26,12,tzinfo=ZONE),factory,t)['status']=='already_sent'


def test_next_send_skips_delivered_date_and_preserves_other_preferences(db,tmp_path):
    s=settings(tmp_path)
    save_report_preferences(db,1,ReportPreferences(send_time='10:00'))
    view=view_report_preferences(db,1,s,datetime(2020,10,26,9,tzinfo=ZONE))
    assert view['next_send']=='2020-10-26T10:00:00+03:00'
    ledger=ReportLedger(tmp_path)
    for channel in ('email','telegram'):ledger.record('1-2020-10-26',channel,'recipient','sent')
    view=view_report_preferences(db,1,s,datetime(2020,10,26,9,tzinfo=ZONE))
    assert view['next_send']=='2020-11-01T10:00:00+03:00'


def test_http_endpoint_validation_and_profile_isolation(tmp_path,monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db.base import Base
    from app.db.models import User
    from app.db.models.auth_identity import AuthIdentity
    from app.db.session import get_db
    from app.api.deps import get_current_user_id
    import app.api.v1.preferences as routes
    engine=create_engine('sqlite:///'+str(tmp_path/'api.sqlite'))
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([User(id=1,status='approved'),User(id=2,status='approved')]);session.flush()
        session.add(AuthIdentity(user_id=1,provider='telegram',provider_user_id='123'));session.commit()
    def session_dep():
        with Session(engine) as session:yield session
    actor={'id':1};app=FastAPI();app.include_router(routes.router)
    app.dependency_overrides[get_db]=session_dep
    app.dependency_overrides[get_current_user_id]=lambda:actor['id']
    monkeypatch.setattr(routes,'get_settings',lambda:settings(tmp_path))
    with TestClient(app) as client:
        assert client.get('/preferences/financial-reports').json()['available']
        assert client.put('/preferences/financial-reports',json={'send_time':'09:07'}).status_code==422
        assert client.put('/preferences/financial-reports',json={'enabled':False}).json()['settings']['enabled'] is False
        actor['id']=2
        assert client.get('/preferences/financial-reports').json()['email_address'] is None
        assert client.put('/preferences/financial-reports',json={'enabled':True}).status_code==403
    engine.dispose()


def test_pause_during_image_generation_prevents_network_send(db,tmp_path,monkeypatch):
    import scripts.run_financial_reports as runner
    original=runner.render_report
    def render(report):
        result=original(report)
        save_report_preferences(db,1,ReportPreferences(enabled=False))
        return result
    monkeypatch.setattr(runner,'render_report',render)
    t=Transport()
    result=runner.run(settings(tmp_path),datetime(2020,10,26,9,tzinfo=ZONE),sessionmaker(bind=db.get_bind()),t)
    assert result['status']=='settings_changed' and t.calls==[]
