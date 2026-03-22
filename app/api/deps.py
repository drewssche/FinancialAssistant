from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.services.auth_context_service import (
    AuthenticatedUserNotFoundError,
    AuthContextService,
    InvalidAccessTokenError,
    InvalidAuthorizationHeaderError,
)


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    try:
        return AuthContextService(db).resolve_user_from_authorization_header(authorization)
    except (
        InvalidAuthorizationHeaderError,
        InvalidAccessTokenError,
        AuthenticatedUserNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _is_admin_user(current_user: User) -> bool:
    settings = get_settings()
    admin_ids = settings.admin_telegram_id_set
    if not admin_ids:
        return False
    for identity in current_user.identities or []:
        if identity.provider == "telegram" and identity.provider_user_id in admin_ids:
            return True
    return False


def get_current_approved_user(current_user: User = Depends(get_current_user)) -> User:
    if _is_admin_user(current_user):
        return current_user
    if current_user.status not in {"approved", "active"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access is not approved",
        )
    return current_user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not _is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_current_user_id(current_user: User = Depends(get_current_approved_user)) -> int:
    return current_user.id


def get_current_user_is_admin(current_user: User = Depends(get_current_user)) -> bool:
    return _is_admin_user(current_user)
