from datetime import datetime, timedelta, timezone
from decimal import Decimal
import importlib.util

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from alembic.migration import MigrationContext
from alembic.operations import Operations

from tests.services.test_financial_reports import db, Transport
from tests.services.test_financial_report_preferences import settings
from app.db.models import User
from app.db.models.financial_report_recipient import FinancialReportRecipient
from app.services.financial_report_preferences import (
    ReportPreferences, save_report_preferences, view_report_preferences, report_recipients,
)
from app.services.financial_report_email import request_code, confirm_code, remove_email, EmailRequest, EmailVerificationError
from app.services.financial_report_data import ZONE
from scripts.run_financial_reports import run

NOW=datetime(2020,10,26,9,tzinfo=ZONE)


def email_settings(tmp_path):
    s=settings(tmp_path)
    s.app_secret_key='test-only-secret'
    s.smtp_host='test.invalid';s.smtp_from='sender@example.test'
    s.smtp_username='test';s.smtp_password='test'
    return s


def test_new_profile_opt_in_and_owner_unchanged(db,tmp_path):
    s=settings(tmp_path)
    old=view_report_preferences(db,1,s,NOW)
    other=view_report_preferences(db,2,s,NOW)
    assert old['email_address']=='owner@example.test' and old['settings']['enabled']
    assert other['available'] and not other['settings']['enabled'] and not other['settings']['email']
    assert other['email_address'] is None
    with pytest.raises(ValueError):save_report_preferences(db,2,ReportPreferences(),s,NOW)
    db.rollback()
    save_report_preferences(db,2,ReportPreferences(email=False),s,NOW)
    assert db.get(FinancialReportRecipient,2).activated_on==NOW.date()
    assert report_recipients(db,2,s)=={'telegram':'456'}
    assert view_report_preferences(db,1,s,NOW)==old


def test_email_swap_is_confirmed_user_bound_and_single_use(db,tmp_path):
    s=email_settings(tmp_path);sent=[]
    sender=lambda _,address,code:sent.append((address,code))
    request_code(db,1,'new@example.test',s,NOW,sender)
    assert report_recipients(db,1,s)['email']=='owner@example.test'
    row=db.get(FinancialReportRecipient,1)
    assert row.code_digest!=sent[0][1] and len(row.code_digest)==64
    with pytest.raises(EmailVerificationError):confirm_code(db,2,*sent[0],s,NOW)
    db.rollback()
    with pytest.raises(EmailVerificationError):confirm_code(db,1,'different@example.test',sent[0][1],s,NOW)
    assert report_recipients(db,1,s)['email']=='owner@example.test'
    confirm_code(db,1,*sent[0],s,NOW)
    assert report_recipients(db,1,s)['email']=='new@example.test'
    with pytest.raises(EmailVerificationError):confirm_code(db,1,*sent[0],s,NOW)
    db.rollback()
    view=view_report_preferences(db,1,s,NOW)
    assert view['pending_email'] is None and 'code_digest' not in str(view)
    save_report_preferences(db,1,ReportPreferences(telegram=False),s,NOW)
    remove_email(db,1,s)
    assert 'email' not in report_recipients(db,1,s)  # Never falls back to legacy env after removal.
    assert not view_report_preferences(db,1,s,NOW)['settings']['enabled']


def test_code_expiry_attempts_cooldown_and_daily_limit(db,tmp_path):
    s=email_settings(tmp_path);sent=[]
    sender=lambda _,address,code:sent.append((address,code))
    request_code(db,2,'other@example.test',s,NOW,sender)
    with pytest.raises(EmailVerificationError) as error:request_code(db,2,'other@example.test',s,NOW,sender)
    assert error.value.status==429
    for i in range(5):
        with pytest.raises(EmailVerificationError):confirm_code(db,2,'wrong@example.test',sent[-1][1],s,NOW)
    with pytest.raises(EmailVerificationError):confirm_code(db,2,*sent[-1],s,NOW)
    for i in range(1,5):request_code(db,2,'other@example.test',s,NOW+timedelta(minutes=i),sender)
    with pytest.raises(EmailVerificationError) as error:request_code(db,2,'other@example.test',s,NOW+timedelta(minutes=5),sender)
    assert error.value.status==429 and len(sent)==5
    with pytest.raises(EmailVerificationError):confirm_code(db,2,*sent[-1],s,NOW+timedelta(minutes=19))
    assert 'email' not in report_recipients(db,2,s)


def test_ambiguous_smtp_does_not_allow_immediate_retry(db,tmp_path):
    s=email_settings(tmp_path)
    def failed(*args):raise TimeoutError('not returned to client')
    with pytest.raises(EmailVerificationError) as error:request_code(db,2,'other@example.test',s,NOW,failed)
    assert error.value.status==502
    with pytest.raises(EmailVerificationError) as error:request_code(db,2,'other@example.test',s,NOW,failed)
    assert error.value.status==429


@pytest.mark.parametrize('address',['a@example.test\r\nBcc: b@example.test','a@example.test,b@example.test','a b@example.test','a@localhost','..a@example.test'])
def test_email_rejects_header_injection_and_multiple_recipients(address):
    with pytest.raises(ValidationError):EmailRequest(email_address=address)


def test_runner_routes_each_profile_and_keeps_dedupe(db,tmp_path):
    s=settings(tmp_path)
    save_report_preferences(db,2,ReportPreferences(email=False),s,NOW)
    sent=[]
    class RoutedTransport(Transport):
        def __init__(self,s,channels,*,recipients):
            super().__init__();self.recipients={c:recipients[c] for c in channels}
        def send(self,channel,report,png,plain,job):
            sent.append((job,channel,self.recipients[channel],Decimal(str(report['current']['cashflow_expense_total']))))
            return {'test':True}
    factory=sessionmaker(bind=db.get_bind())
    result=run(s,NOW,factory,transport_factory=RoutedTransport)
    assert all(r['status']=='processed' for r in result['users'])
    assert sent==[('1-2020-10-26','telegram','123',Decimal(10)),('1-2020-10-26','email','owner@example.test',Decimal(10)),('2-2020-10-26','telegram','456',Decimal(99999))]
    run(s,NOW,factory,transport_factory=RoutedTransport)
    assert len(sent)==3
    db.get(User,2).status='rejected';db.commit()
    assert not view_report_preferences(db,2,s,NOW)['available']
    assert report_recipients(db,2,s)=={}


def test_one_profile_failure_does_not_stop_another(db,tmp_path,monkeypatch):
    import scripts.run_financial_reports as runner
    s=settings(tmp_path);save_report_preferences(db,2,ReportPreferences(email=False),s,NOW)
    original=runner.collect_report
    def collect(session,owner,*args,**kwargs):
        if owner==1:raise RuntimeError('private diagnostic')
        return original(session,owner,*args,**kwargs)
    monkeypatch.setattr(runner,'collect_report',collect)
    t=Transport();t.recipients={'telegram':'456'}
    result=run(s,NOW,sessionmaker(bind=db.get_bind()),t)
    assert result['users'][0]=={'user_id':1,'status':'failed','error_type':'RuntimeError'}
    assert result['users'][1]['channels']=={'telegram':'sent'}


def test_new_activation_never_catches_up_older_reports(db,tmp_path):
    s=settings(tmp_path)
    save_report_preferences(db,1,ReportPreferences(enabled=False),s,NOW)
    save_report_preferences(db,2,ReportPreferences(email=False),s,NOW+timedelta(days=1))
    result=run(s,NOW+timedelta(days=1),sessionmaker(bind=db.get_bind()),Transport())
    assert result['users'][1]['status']=='not_due'


def test_migration_adds_private_table_and_preserves_existing_users():
    spec=importlib.util.spec_from_file_location('recipients_migration','alembic/versions/20261027_0056_report_recipients.py')
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    engine=create_engine('sqlite:///:memory:')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE users(id INTEGER PRIMARY KEY)'))
        connection.execute(text('INSERT INTO users VALUES(1)'))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            connection.execute(text('INSERT INTO financial_report_recipients(user_id,code_attempts,code_day_count) VALUES(1,0,0)'))
            with pytest.raises(RuntimeError):migration.downgrade()
            assert connection.execute(text('SELECT count(*) FROM users')).scalar()==1
    engine.dispose()


def test_email_routes_use_authenticated_profile_and_hide_verification_state(tmp_path,monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from app.db.base import Base
    from app.db.models.auth_identity import AuthIdentity
    from app.db.session import get_db
    from app.api.deps import get_current_user_id
    import app.api.v1.preferences as routes
    import app.services.financial_report_email as emails
    engine=create_engine('sqlite:///'+str(tmp_path/'api.sqlite'))
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([User(id=1,status='approved'),User(id=2,status='approved')]);session.flush()
        session.add_all([AuthIdentity(user_id=1,provider='telegram',provider_user_id='123'),AuthIdentity(user_id=2,provider='telegram',provider_user_id='456')]);session.commit()
    def session_dep():
        with Session(engine) as session:yield session
    actor={'id':2};app=FastAPI();app.include_router(routes.router)
    app.dependency_overrides[get_db]=session_dep;app.dependency_overrides[get_current_user_id]=lambda:actor['id']
    monkeypatch.setattr(routes,'get_settings',lambda:email_settings(tmp_path))
    sent=[];monkeypatch.setattr(emails,'send_code',lambda s,address,code:sent.append((address,code)))
    base='/preferences/financial-reports'
    with TestClient(app) as client:
        assert client.post(base+'/email/request',json={'user_id':1,'email_address':'other@example.test'}).status_code==422
        response=client.post(base+'/email/request',json={'email_address':'other@example.test'})
        assert response.status_code==200 and response.json()['email_address'] is None
        assert 'code_digest' not in response.text and sent[0][1] not in response.text
        actor['id']=1
        assert client.post(base+'/email/confirm',json={'email_address':sent[0][0],'code':sent[0][1]}).status_code==400
        assert client.get(base).json()['email_address']=='owner@example.test'
        actor['id']=2
        assert client.post(base+'/email/confirm',json={'email_address':sent[0][0],'code':sent[0][1]}).json()['email_address']=='other@example.test'
        assert client.put(base,json=ReportPreferences().model_dump()).status_code==200
        assert client.delete(base+'/email').json()['email_address'] is None
    engine.dispose()
