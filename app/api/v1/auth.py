from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_approved_user
from app.core.config import get_settings
from app.core.security import create_access_token, get_access_token_expiration
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import AuthPublicConfig, TelegramAuthRequest, TelegramBrowserAuthRequest, TokenResponse
from app.services.auth_context_service import AuthContextService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(token: str) -> TokenResponse:
    return TokenResponse(access_token=token, expires_at=get_access_token_expiration(token))


@router.get("/public-config", response_model=AuthPublicConfig)
def get_auth_public_config():
    settings = get_settings()
    username = settings.normalized_telegram_bot_username or None
    return AuthPublicConfig(
        telegram_bot_username=username,
        browser_login_available=settings.browser_telegram_login_enabled,
    )


@router.post("/telegram", response_model=TokenResponse)
def auth_telegram(payload: TelegramAuthRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        token = service.login_with_telegram(payload.init_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _token_response(token)


@router.post("/telegram/browser", response_model=TokenResponse)
def auth_telegram_browser(payload: TelegramBrowserAuthRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.browser_telegram_login_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Browser Telegram login is not configured",
        )
    service = AuthService(db)
    try:
        token = service.login_with_telegram_browser(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _token_response(token)


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    authorization: str | None = Header(default=None),
    current_user: User = Depends(get_current_approved_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    payload = AuthContextService(db).resolve_token_payload_from_authorization_header(authorization)
    now = datetime.now(timezone.utc)
    session_started_at = int(payload.get("session_started_at") or payload.get("iat") or now.timestamp())
    session_age_seconds = int(now.timestamp()) - session_started_at
    if session_age_seconds >= settings.app_session_max_hours * 3600:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Maximum session lifetime reached",
        )
    token = create_access_token({"sub": str(current_user.id), "session_started_at": session_started_at})
    return _token_response(token)
