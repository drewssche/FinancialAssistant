from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.metrics import get_dashboard_summary_metrics
from app.db.session import get_db
from app.schemas.dashboard import (
    AnalyticsCalendarOut,
    AnalyticsCalendarYearOut,
    AnalyticsHighlightsOut,
    AnalyticsTrendOut,
    DashboardDebtPreviewCard,
    DashboardSummary,
    DashboardSummaryMetrics,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    period: str = Query(default="month", pattern="^(day|week|month|year|all_time|custom)$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    try:
        return service.get_summary(user_id=user_id, period=period, date_from=date_from, date_to=date_to)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/summary/metrics", response_model=DashboardSummaryMetrics)
def get_summary_metrics(user_id: int = Depends(get_current_user_id)):
    _ = user_id
    return get_dashboard_summary_metrics()


@router.get("/debts/preview", response_model=list[DashboardDebtPreviewCard])
def get_debt_preview(
    limit: int = Query(default=6, ge=1, le=12),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    return service.get_debt_preview(user_id=user_id, limit_cards=limit)


@router.get("/analytics/calendar", response_model=AnalyticsCalendarOut)
def get_analytics_calendar(
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    month_anchor = None
    if month:
        try:
            month_anchor = datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month format") from exc
    return service.get_analytics_calendar(user_id=user_id, month_anchor=month_anchor)


@router.get("/analytics/trend", response_model=AnalyticsTrendOut)
def get_analytics_trend(
    period: str = Query(default="month", pattern="^(day|week|month|year|all_time|custom)$"),
    granularity: str = Query(default="day", pattern="^(day|week|month|year)$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    try:
        return service.get_analytics_trend(
            user_id=user_id,
            period=period,
            date_from=date_from,
            date_to=date_to,
            granularity=granularity,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/analytics/calendar/year", response_model=AnalyticsCalendarYearOut)
def get_analytics_calendar_year(
    year: int | None = Query(default=None, ge=1970, le=2100),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    return service.get_analytics_calendar_year(user_id=user_id, year_anchor=year)


@router.get("/analytics/highlights", response_model=AnalyticsHighlightsOut)
def get_analytics_highlights(
    period: str = Query(default="month", pattern="^(day|week|month|year|all_time|custom)$"),
    category_kind: str = Query(default="expense", pattern="^(expense|income|all)$"),
    category_breakdown_level: str = Query(default="category", pattern="^(category|group)$"),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    month_anchor = None
    if month:
        try:
            month_anchor = datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month format") from exc
    try:
        return service.get_analytics_highlights(
            user_id=user_id,
            period=period,
            category_kind=category_kind,
            category_breakdown_level=category_breakdown_level,
            date_from=date_from,
            date_to=date_to,
            month_anchor=month_anchor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
