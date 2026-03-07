from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.auth import AuthPublicConfig, TelegramAuthRequest, TelegramBrowserAuthRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/public-config", response_model=AuthPublicConfig)
def get_auth_public_config():
    settings = get_settings()
    username = (settings.telegram_bot_username or "").strip() or None
    return AuthPublicConfig(
        telegram_bot_username=username,
        browser_login_available=bool(username),
    )


@router.post("/telegram", response_model=TokenResponse)
def auth_telegram(payload: TelegramAuthRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        token = service.login_with_telegram(payload.init_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return TokenResponse(access_token=token)


@router.post("/telegram/browser", response_model=TokenResponse)
def auth_telegram_browser(payload: TelegramBrowserAuthRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        token = service.login_with_telegram_browser(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return TokenResponse(access_token=token)
