from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    period: str = Query(default="30d", pattern="^(30d|month)$"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    return service.get_summary(user_id=user_id, period=period)
