from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.preferences import PreferencesOut, PreferencesPayload
from app.services.preferences_service import PreferencesService
from app.core.config import get_settings
from app.services.financial_report_preferences import (
    ReportPreferences, configured_for, save_report_preferences, view_report_preferences,
)

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=PreferencesOut)
def get_preferences(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = PreferencesService(db)
    return service.get_preferences(user_id)


@router.put("", response_model=PreferencesOut)
def update_preferences(
    payload: PreferencesPayload,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = PreferencesService(db)
    return service.update_preferences(
        user_id=user_id,
        preferences_version=payload.preferences_version,
        data=payload.data,
    )


@router.get("/financial-reports")
def get_financial_report_preferences(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return view_report_preferences(db, user_id, get_settings())


@router.put("/financial-reports")
def update_financial_report_preferences(payload: ReportPreferences, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    settings = get_settings()
    if not configured_for(db, user_id, settings):
        raise HTTPException(status_code=403, detail="Рассылка для этого профиля не подключена")
    save_report_preferences(db, user_id, payload)
    return view_report_preferences(db, user_id, settings)
