"""Owner-scoped financial snapshots; use the same historical cashflows as the UI."""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db.models.auth_identity import AuthIdentity
from app.db.models.user import User
from app.repositories.operation_repo import OperationRepository
from app.services.dashboard_analytics import DashboardAnalyticsService
from app.services.plan_service import PlanService

ZONE = ZoneInfo('Europe/Minsk')


@dataclass(frozen=True)
class ReportPeriod:
    kind: str
    start: date
    end: date
    due: date


def scheduled_period(day: date) -> ReportPeriod | None:
    # A single decision, not three independent cron jobs: year > month > week.
    if day.month == 1 and day.day == 1:
        return ReportPeriod('year', date(day.year - 1, 1, 1), day - timedelta(days=1), day)
    if day.day == 1:
        end = day - timedelta(days=1)
        return ReportPeriod('month', end.replace(day=1), end, day)
    if day.weekday() == 0:
        return ReportPeriod('week', day - timedelta(days=7), day - timedelta(days=1), day)
    return None


def latest_due(now: datetime, enabled_from: date) -> ReportPeriod | None:
    """Catch up only the latest eligible release within seven days, never a backlog."""
    if now.tzinfo is None:
        raise ValueError('Aware clock required')
    local = now.astimezone(ZONE)
    for offset in range(7):
        day = local.date() - timedelta(days=offset)
        if day < enabled_from:
            break
        if offset == 0 and local.hour < 9:
            continue
        period = scheduled_period(day)
        if period:
            return period
    return None


def previous_period(p: ReportPeriod) -> tuple[date, date]:
    if p.kind == 'year':
        return date(p.start.year - 1, 1, 1), date(p.end.year - 1, p.end.month, min(p.end.day, monthrange(p.end.year - 1, p.end.month)[1]))
    if p.kind == 'month':
        last = p.start.replace(day=1) - timedelta(days=1)
        # Full months compare with full months; partial previews with matching days.
        end = last if p.end.day == monthrange(p.end.year, p.end.month)[1] else last.replace(day=min(p.end.day, last.day))
        return last.replace(day=1), end
    return p.start - timedelta(days=7), p.end - timedelta(days=7)


def resolve_owner(db, telegram_id: str) -> int:
    ids = list(db.scalars(select(AuthIdentity.user_id).join(User, User.id == AuthIdentity.user_id).where(
        AuthIdentity.provider == 'telegram', AuthIdentity.provider_user_id == telegram_id,
        User.status == 'approved',
    )))
    if len(ids) != 1:
        raise ValueError('Report recipient must map to one approved owner')
    return int(ids[0])


def plan_label(item: dict) -> str:
    parts = []
    for line in item.get('receipt_items', []):
        name = str(line.get('name') or line.get('product_name') or '').strip()
        source = str(line.get('source_name') or line.get('shop_name') or '').strip()
        value = ' · '.join(x for x in (source, name) if x)
        if value and value not in parts:
            parts.append(value)
    if parts:
        return '; '.join(parts)
    return str(item.get('note') or '').strip() or f"{item.get('category_name') or 'Платёж'} · название не указано"


def collect_report(db, user_id: int, period: ReportPeriod, *, today: date) -> dict:
    repo = OperationRepository(db)
    a = DashboardAnalyticsService(db, repo)
    def highlights(start, end):
        return a.get_highlights(user_id=user_id, period='custom', date_from=start, date_to=end)
    current = highlights(period.start, period.end)
    previous = highlights(*previous_period(period))
    top = current.get('top_operations', [])[:3]
    receipt_map = repo.list_receipt_items_for_operations(user_id=user_id, operation_ids=[x['operation_id'] for x in top])
    for item in top:
        lines = receipt_map.get(item['operation_id'], [])
        shops = list(dict.fromkeys(line.shop_name for line in lines if line.shop_name))
        item['report_label'] = str(item.get('note') or '').strip() or (' · '.join(shops) if shops else 'Расход без комментария')
        item['receipt_summary'] = ', '.join(line.name for line in lines[:2])
        item['receipt_count'] = len(lines)
    series = []
    if period.kind == 'year':
        for month in range(1, period.end.month + 1):
            start = date(period.start.year, month, 1)
            end = min(period.end, date(start.year, month, monthrange(start.year, month)[1]))
            value = highlights(start, end)
            series.append({k: value[k] for k in ('date_from', 'date_to', 'cashflow_total', 'cashflow_expense_total')})
    else:
        cursor = period.start
        # Group a monthly report into consecutive 7-day intervals, last one partial.
        step = 1 if period.kind == 'week' else 7
        while cursor <= period.end:
            end = min(period.end, cursor + timedelta(days=step - 1))
            value = highlights(cursor, end)
            series.append({k: value[k] for k in ('date_from', 'date_to', 'cashflow_total', 'cashflow_expense_total')})
            cursor = end + timedelta(days=1)
    forecast = PlanService(db).forecast(user_id=user_id, days=7, today=today, include_details=True)
    for item in forecast['occurrences'] + forecast['overdue_items']:
        item['report_label'] = plan_label(item)
    # Small secondary summaries on collision days, inside this same report.
    supplements = []
    if period.kind == 'year' and period.end.month == 12:
        supplements.append({'label': 'Декабрь', 'data': highlights(date(period.end.year, 12, 1), period.end)})
    if period.kind != 'week' and period.due.weekday() == 0:
        supplements.append({'label': 'Прошлая неделя', 'data': highlights(period.due - timedelta(days=7), period.due - timedelta(days=1))})
    result = dict(kind=period.kind, start=period.start, end=period.end, due=period.due,
                  generated_on=today, currency=a.highlights.get_user_base_currency(user_id),
                  current=current, previous=previous, series=series, plans=forecast, supplements=supplements)
    verify_totals(result)
    return result


def verify_totals(report):
    current = report['current']
    dec = lambda key: Decimal(str(current[key]))
    if dec('cashflow_income_total') - dec('cashflow_expense_total') != dec('cashflow_total'):
        raise ValueError('Financial report does not reconcile')
    if dec('income_total') - dec('expense_total') + dec('debt_cashflow_total') + dec('fx_cashflow_total') != dec('cashflow_total'):
        raise ValueError('Report components do not reconcile')
    if sum(Decimal(str(x['cashflow_total'])) for x in report['series']) != dec('cashflow_total'):
        raise ValueError('Report chart does not reconcile')
