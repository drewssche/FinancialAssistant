from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.auth import DevAuthRequest, TelegramAuthRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram", response_model=TokenResponse)
def auth_telegram(payload: TelegramAuthRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        token = service.login_with_telegram(payload.init_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return TokenResponse(access_token=token)


@router.post("/dev", response_model=TokenResponse)
def auth_dev(payload: DevAuthRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    if settings.app_env.lower() == "production":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev auth is disabled in production")

    service = AuthService(db)
    token = service.login_dev(
        telegram_id=payload.telegram_id,
        first_name=payload.first_name,
        username=payload.username,
        avatar_url=payload.avatar_url,
    )
    return TokenResponse(access_token=token)
