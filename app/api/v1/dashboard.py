from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.metrics import get_dashboard_summary_metrics
from app.db.session import get_db
from app.schemas.dashboard import DashboardSummary, DashboardSummaryMetrics
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
