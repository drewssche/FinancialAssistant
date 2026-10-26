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

from app.services.financial_report_email import (
    EmailRequest, EmailConfirmation, EmailVerificationError, request_code, confirm_code, remove_email,
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
    try:
        save_report_preferences(db, user_id, payload, settings)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return view_report_preferences(db, user_id, settings)


def require_reports(db,user_id):
    settings=get_settings()
    if not configured_for(db,user_id,settings):
        raise HTTPException(status_code=403,detail="Войдите через Telegram в одобренный профиль")
    return settings


@router.post("/financial-reports/email/request")
def request_report_email(payload: EmailRequest,user_id: int=Depends(get_current_user_id),db: Session=Depends(get_db)):
    settings=require_reports(db,user_id)
    try:request_code(db,user_id,payload.email_address,settings)
    except EmailVerificationError as error:raise HTTPException(status_code=error.status,detail=str(error)) from None
    return view_report_preferences(db,user_id,settings)


@router.post("/financial-reports/email/confirm")
def confirm_report_email(payload: EmailConfirmation,user_id: int=Depends(get_current_user_id),db: Session=Depends(get_db)):
    settings=require_reports(db,user_id)
    try:confirm_code(db,user_id,payload.email_address,payload.code,settings)
    except EmailVerificationError as error:raise HTTPException(status_code=error.status,detail=str(error)) from None
    return view_report_preferences(db,user_id,settings)


@router.delete("/financial-reports/email")
def delete_report_email(user_id: int=Depends(get_current_user_id),db: Session=Depends(get_db)):
    settings=require_reports(db,user_id)
    remove_email(db,user_id,settings)
    return view_report_preferences(db,user_id,settings)
