from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
import json
from types import SimpleNamespace

from PIL import Image
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import User, Category, Operation, PlanOperation, PlanReceiptItem
from app.db.models.auth_identity import AuthIdentity
from app.services.financial_report_data import (
    ReportPeriod, ZONE, scheduled_period, latest_due, previous_period,
    collect_report, plan_label, resolve_owner,
)
from app.services.financial_report_delivery import ReportLedger, ReportTransport
from app.services.financial_report_renderer import render_report
from app.services.plan_service import PlanService


@pytest.mark.parametrize('due,kind,start,end', [
    ('2029-01-01', 'year', '2028-01-01', '2028-12-31'),  # Monday AND month AND year
    ('2027-02-01', 'month', '2027-01-01', '2027-01-31'), # Monday AND month
    ('2026-11-01', 'month', '2026-10-01', '2026-10-31'),
    ('2026-11-02', 'week', '2026-10-26', '2026-11-01'),
    ('2024-03-01', 'month', '2024-02-01', '2024-02-29'),
    ('2026-10-26', 'week', '2026-10-19', '2026-10-25'),
])
def test_calendar_collision_priority_and_complete_periods(due, kind, start, end):
    p = scheduled_period(date.fromisoformat(due))
    assert (p.kind, str(p.start), str(p.end)) == (kind, start, end)


def test_local_nine_activation_and_bounded_outage_catchup():
    activation = date(2026, 10, 26)
    assert latest_due(datetime(2026,10,26,5,59,tzinfo=timezone.utc), activation) is None
    assert latest_due(datetime(2026,10,26,6,0,tzinfo=timezone.utc), activation).due == activation
    assert latest_due(datetime(2026,10,29,10,tzinfo=ZONE), activation).due == activation
    assert latest_due(datetime(2026,11,2,10,tzinfo=ZONE), activation).due == date(2026,11,2)
    assert latest_due(datetime(2026,10,26,12,tzinfo=ZONE), date(2026,10,27)) is None
    with pytest.raises(ValueError): latest_due(datetime(2026,10,26,12), activation)


def test_full_month_comparison_not_equal_day_count_and_leap_year():
    p=scheduled_period(date(2026,11,1))
    assert previous_period(p) == (date(2026,9,1),date(2026,9,30))
    p=ReportPeriod('year',date(2024,1,1),date(2024,2,29),date(2024,3,1))
    assert previous_period(p) == (date(2023,1,1),date(2023,2,28))


class Transport:
    recipients={'telegram':'123','email':'owner@example.test'}
    def __init__(self): self.calls=[]; self.fail=None; self.preflight_fail=None
    def preflight(self, channel):
        if channel==self.preflight_fail: raise ValueError('secret-credential')
    def send(self, channel, *args):
        self.calls.append(channel)
        if channel==self.fail: raise RuntimeError('bot-token smtp-secret')
        return {'accepted':True}


def test_channels_restart_and_uncertain_send_are_never_replayed(tmp_path):
    t=Transport();t.fail='email';l=ReportLedger(tmp_path)
    with l.lock() as locked:
        assert locked
        assert l.deliver('job',t,{},b'png','plain')=={'telegram':'sent','email':'uncertain'}
    l=ReportLedger(tmp_path);t.fail=None
    with l.lock(): l.deliver('job',t,{},b'png','plain')
    assert t.calls==['telegram','email']
    with l.connect() as db: rows=[tuple(x) for x in db.execute('SELECT * FROM events')]
    assert 'secret' not in json.dumps(rows) and 'bot-token' not in json.dumps(rows)


def test_preflight_failure_can_recover_without_repeating_other_channel(tmp_path):
    l=ReportLedger(tmp_path);t=Transport();t.preflight_fail='email'
    with l.lock(): l.deliver('job',t,{},b'', '')
    assert t.calls==['telegram']
    t.preflight_fail=None
    with l.lock(): l.deliver('job',t,{},b'', '')
    assert t.calls==['telegram','email']


def test_crash_between_send_and_ack_is_reserved_and_concurrent_run_excluded(tmp_path):
    l=ReportLedger(tmp_path);other=ReportLedger(tmp_path)
    with l.lock() as acquired:
        assert acquired
        with other.lock() as second: assert not second
        l.record('job','telegram','123','sending')
    t=Transport()
    with other.lock(): other.deliver('job',t,{},b'', '')
    assert t.calls==['email'] and other.state('job','telegram')=='uncertain'


@pytest.fixture
def db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([User(id=1,status='approved'),User(id=2,status='approved')]);db.flush()
        db.add_all([AuthIdentity(user_id=1,provider='telegram',provider_user_id='123'),AuthIdentity(user_id=2,provider='telegram',provider_user_id='456'),
                    Category(id=1,user_id=1,kind='expense',name='Подписки')]);db.flush()
        db.add_all([Operation(user_id=1,kind='income',amount=100,original_amount=100,currency='BYN',base_currency='BYN',fx_rate=1,operation_date=date(2020,10,20)),
                    Operation(user_id=1,kind='expense',amount=10,original_amount=10,currency='BYN',base_currency='BYN',fx_rate=1,operation_date=date(2020,10,21),category_id=1,note='Подписка'),
                    Operation(user_id=2,kind='expense',amount=99999,original_amount=99999,currency='BYN',base_currency='BYN',fx_rate=1,operation_date=date(2020,10,21))])
        db.add(PlanOperation(id=1,user_id=1,kind='expense',amount=Decimal('2.99'),original_amount=Decimal('2.99'),currency='BYN',base_currency='BYN',category_id=1,scheduled_date=date(2020,10,28),status='active'))
        db.flush()
        db.add(PlanReceiptItem(plan_id=1,user_id=1,name='На месяц',shop_name='Eleven',quantity=1,unit_price=Decimal('2.99'),line_total=Decimal('2.99')))
        db.commit()
        yield db
    engine.dispose()


def test_real_snapshot_is_owner_scoped_and_includes_plan_receipt_name(db):
    assert resolve_owner(db,'123')==1
    with pytest.raises(ValueError): resolve_owner(db,'999')
    p=scheduled_period(date(2020,10,26))
    result=collect_report(db,1,p,today=p.due)
    assert result['current']['cashflow_income_total']==Decimal('100')
    assert result['current']['cashflow_expense_total']==Decimal('10')
    item=result['plans']['occurrences'][0]
    assert item['report_label']=='Eleven · На месяц'
    assert item['scheduled_date']==date(2020,10,28)
    assert db.get(PlanOperation,1).scheduled_date==date(2020,10,28)
    png,plain=render_report(result)
    image=Image.open(BytesIO(png))
    assert image.width==1080 and 900<image.height<3000
    assert 'Eleven · На месяц' in plain and '99999' not in plain
    assert 'ДЕМО' not in plain and 'Пример' not in plain


def test_plan_forecast_details_preserve_default_contract_and_recurrence(db):
    plan=db.get(PlanOperation,1);plan.recurrence_enabled=True;plan.recurrence_frequency='daily';plan.recurrence_interval=2;db.commit()
    service=PlanService(db)
    plain=service.forecast(user_id=1,today=date(2020,10,28),days=7)
    rich=service.forecast(user_id=1,today=date(2020,10,28),days=7,include_details=True)
    assert {k:v for k,v in rich.items() if k not in ['occurrences','overdue_items']}==plain
    assert plain['occurrences_count']==4
    assert len(rich['occurrences'])==4
    assert plan_label(rich['occurrences'][0])=='Eleven · На месяц'
    assert plan.scheduled_date==date(2020,10,28)


def test_long_titles_empty_period_and_year_plot_fit(db):
    result=collect_report(db,1,ReportPeriod('year',date(2020,1,1),date(2020,12,31),date(2021,1,1)),today=date(2021,1,1))
    for category in result['current']['category_breakdown']: category['category_name']='Очень длинное название категории '*20
    for item in result['plans']['overdue_items']: item['report_label']='Очень длинная подписка '*30
    png,plain=render_report(result)
    assert Image.open(BytesIO(png)).height<6400
    assert 'Декабрь' in plain
    empty=collect_report(db,2,scheduled_period(date(2019,1,7)),today=date(2019,1,7))
    png,plain=render_report(empty)
    assert 'За период расходов нет.' in plain


def test_telegram_preflight_requires_matching_private_chat(monkeypatch):
    import app.services.financial_report_delivery as m
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self,*args,**kwargs):
            return SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'ok':True,'result':{'id':123,'type':'group'}})
    monkeypatch.setattr(m.httpx,'Client',Client)
    settings=SimpleNamespace(financial_reports_telegram_id='123',financial_reports_email='o@example.test',telegram_bot_token='secret')
    with pytest.raises(ValueError):ReportTransport(settings).preflight('telegram')


def test_runner_persists_snapshot_and_skips_sent_channels_after_restart(db,tmp_path):
    from scripts.run_financial_reports import run
    from sqlalchemy.orm import sessionmaker
    settings=SimpleNamespace(financial_reports_enabled=True,financial_reports_start_date=date(2020,10,26),
        financial_reports_state_dir=str(tmp_path),financial_reports_telegram_id='123',financial_reports_email='owner@example.test')
    transport=Transport();now=datetime(2020,10,26,9,tzinfo=ZONE)
    factory=sessionmaker(bind=db.get_bind())
    first=run(settings,now,factory,transport)
    assert first['channels']=={'telegram':'sent','email':'sent'}
    assert run(settings,now,factory,transport)['status']=='already_sent'
    assert transport.calls==['telegram','email']
    snapshot=json.loads((tmp_path/'1-2020-10-26'/'report.json').read_text())
    assert snapshot['current']['cashflow_total']=='90.00'
    assert (tmp_path/'1-2020-10-26'/'report.png').is_file()


def test_email_contains_inline_png_and_plain_accessible_report(monkeypatch):
    import app.services.financial_report_delivery as m
    messages=[]
    class SMTP:
        def __init__(self,*args,**kwargs): pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def login(self,*args):pass
        def send_message(self,msg):messages.append(msg);return {}
    monkeypatch.setattr(m.smtplib,'SMTP_SSL',SMTP)
    settings=SimpleNamespace(financial_reports_telegram_id='123',financial_reports_email='owner@example.test',
        smtp_from='sender@example.test',smtp_host='smtp.example.test',smtp_port=465,smtp_security='ssl',smtp_username='user',smtp_password='secret')
    report={'kind':'week','start':'2020-10-19','end':'2020-10-25','currency':'BYN',
        'current':{'cashflow_income_total':100,'cashflow_expense_total':10,'cashflow_total':90}}
    t=ReportTransport(settings);t.preflight('email')
    assert t.send('email',report,b'png-content','Readable text','1-2020-10-26')=={'smtp_accepted':True}
    message=messages[0]
    assert message['To']=='owner@example.test'
    assert message.get_body(preferencelist=('plain',)).get_content().strip()=='Readable text'
    assert 'cid:financial-report' in message.get_body(preferencelist=('html',)).get_content()
    image_parts=[x for x in message.walk() if x.get_content_type()=='image/png']
    assert len(image_parts)==1 and image_parts[0].get_payload(decode=True)==b'png-content'


@pytest.mark.parametrize('kind,start,end', [
    ('week', '2019-12-23', '2019-12-29'),
    ('month', '2019-12-01', '2019-12-31'),
    ('year', '2019-01-01', '2019-12-31'),
])
def test_compact_layouts_handle_empty_periods_offline(db, monkeypatch, kind, start, end):
    import socket
    monkeypatch.setattr(socket, 'create_connection', lambda *a, **k: pytest.fail('Renderer must stay offline'))
    period = ReportPeriod(kind, date.fromisoformat(start), date.fromisoformat(end), date(2020,1,1))
    result = collect_report(db, 2, period, today=period.due)
    png, plain = render_report(result)
    image = Image.open(BytesIO(png))
    assert image.width == 1080 and 900 < image.height < 3000
    assert 'Пришло: 0,00' in plain and 'Ушло: 0,00' in plain
    assert 'Разница: 0,00' in plain and 'За период расходов нет.' in plain
    if kind == 'year':
        assert all(month+': 0,00' in plain for month in ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'])


def test_ring_keeps_operating_expenses_distinct_from_total_outflow_and_keeps_remainder(db):
    result = collect_report(db, 1, ReportPeriod('month',date(2020,10,1),date(2020,10,31),date(2020,11,1)),today=date(2020,11,1))
    current = result['current']
    current.update(cashflow_expense_total=Decimal('260'), expense_total=Decimal('210'), cashflow_total=Decimal('-160'))
    current['category_breakdown'] = [dict(category_name='Новая категория '+str(i), total_amount=Decimal(i*10)) for i in range(1,7)]
    png, plain = render_report(result)
    assert 'Ушло: 260,00' in plain and 'Расходы по операциям: 210,00' in plain
    assert 'Разница: -160,00' in plain and 'Остальные категории: 10,00' in plain
    assert Image.open(BytesIO(png)).height < 3000


def test_renderer_update_does_not_replace_cached_image_or_resend_delivered_channel(db,tmp_path,monkeypatch):
    import scripts.run_financial_reports as runner
    from sqlalchemy.orm import sessionmaker
    settings=SimpleNamespace(financial_reports_enabled=True,financial_reports_start_date=date(2020,10,26),
        financial_reports_state_dir=str(tmp_path),financial_reports_telegram_id='123',financial_reports_email='owner@example.test')
    transport=Transport(); transport.preflight_fail='email'
    now=datetime(2020,10,26,9,tzinfo=ZONE); factory=sessionmaker(bind=db.get_bind())
    assert runner.run(settings,now,factory,transport)['channels']=={'telegram':'sent','email':'preflight_failed'}
    cached=(tmp_path/'1-2020-10-26'/'report.png').read_bytes()
    monkeypatch.setattr(runner,'render_report',lambda report: pytest.fail('Existing delivery must reuse its image'))
    transport.preflight_fail=None
    assert runner.run(settings,now,factory,transport)['channels']=={'telegram':'sent','email':'sent'}
    assert transport.calls==['telegram','email']
    assert (tmp_path/'1-2020-10-26'/'report.png').read_bytes()==cached
