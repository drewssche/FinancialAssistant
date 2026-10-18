from datetime import date, timedelta
from decimal import Decimal
from app.main import app
from app.db.session import get_db
from app.db.models import PlanOperation, User
from app.services.plan_service import PlanService
from tests.api.test_dashboard_api import client


def test_current_month_uses_elapsed_days_and_gross_flows(client, monkeypatch):
    class Today(date):
        @classmethod
        def today(cls): return cls(2026, 10, 18)
    monkeypatch.setattr('app.services.dashboard_analytics_highlights.date', Today)
    for day, kind, amount in [('2026-10-02','income','100'), ('2026-10-03','expense','36'),
                              ('2026-09-02','expense','18'), ('2026-09-25','expense','900')]:
        r=client.post('/api/v1/operations',json={'kind':kind,'amount':amount,'operation_date':day})
        assert r.status_code==201,r.text
    r=client.post('/api/v1/debts',json={'counterparty':'Test','direction':'borrow','principal':'50','start_date':'2026-10-04'})
    assert r.status_code==201,r.text
    debt=r.json()
    r=client.post(f"/api/v1/debts/{debt['id']}/repayments",json={'amount':'20','repayment_date':'2026-10-05'})
    assert r.status_code==201,r.text
    r=client.get('/api/v1/dashboard/analytics/highlights',params={'period':'month','month':'2026-10'})
    assert r.status_code==200,r.text
    d=r.json()
    assert d['date_to']=='2026-10-18'
    assert d['comparison_date_from']=='2026-09-01' and d['comparison_date_to']=='2026-09-18'
    assert Decimal(d['avg_daily_expense'])==2
    assert Decimal(d['prev_expense_total'])==18
    assert Decimal(d['cashflow_income_total'])==150
    assert Decimal(d['cashflow_expense_total'])==56
    assert Decimal(d['cashflow_total'])==94


def test_forecast_repeats_end_date_ownership_and_no_writes(client):
    gen=app.dependency_overrides[get_db](); db=next(gen)
    try:
        db.add(User(id=2,display_name='Other',status='active'))
        for uid, amount in [(1,10),(2,999)]:
            db.add(PlanOperation(user_id=uid,kind='expense',amount=amount,original_amount=amount,
                scheduled_date=date(2026,10,1),recurrence_enabled=True,recurrence_frequency='weekly',
                recurrence_interval=1,recurrence_end_date=date(2026,10,22),status='active'))
        db.add(PlanOperation(user_id=1,kind='income',amount=100,original_amount=100,
            scheduled_date=date(2026,10,2),status='active'))
        db.commit()
        result=PlanService(db).forecast(user_id=1,days=30,today=date(2026,10,1))
        assert result['income_total']==100
        assert result['expense_total']==40
        assert result['occurrences_count']==5
        assert not db.dirty and not db.new
        assert all(x.scheduled_date==date(2026,10,1) for x in db.query(PlanOperation).filter_by(kind='expense'))
        result=PlanService(db).forecast(user_id=1,days=7,today=date(2026,10,8))
        assert result['expense_total']==10 and result['overdue_count']==2
    finally: gen.close()


def test_forecast_endpoint_validates_horizon(client):
    for days in [0,367]:
        assert client.get('/api/v1/plans/forecast',params={'days':days}).status_code==422
    r=client.get('/api/v1/plans/forecast',params={'days':7})
    assert r.status_code==200,r.text
    assert r.json()['occurrences_count']==0


def test_forecast_marks_missing_rate_instead_of_zero_cost(client):
    gen=app.dependency_overrides[get_db](); db=next(gen)
    try:
        db.add(PlanOperation(user_id=1,kind='expense',amount=30,original_amount=10,
            currency='USD',base_currency='BYN',scheduled_date=date(2026,10,1),status='active'))
        db.commit()
        result=PlanService(db).forecast(user_id=1,days=7,today=date(2026,10,1))
        assert result['occurrences_count']==1 and result['unpriced_count']==1
        assert result['expense_total']==0
    finally: gen.close()
